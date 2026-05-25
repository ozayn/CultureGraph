"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { format } from "date-fns";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import {
  ADMIN_TAB_LABELS,
  ADMIN_TAB_PATHS,
  type AdminAnnotationRecord,
  type AdminArtworkRecord,
  type AdminEntityRecord,
  type AdminPaginated,
  type AdminResearchNoteRecord,
  type AdminSummary,
  type AdminTab,
  type AdminVisitRecord,
} from "@/lib/admin-types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

type AdminRecord =
  | AdminVisitRecord
  | AdminArtworkRecord
  | AdminAnnotationRecord
  | AdminEntityRecord
  | AdminResearchNoteRecord;

interface DeleteTarget {
  tab: AdminTab;
  id: number;
  artworkId?: number;
  label: string;
}

function formatDate(value: string) {
  try {
    return format(new Date(value), "MMM d, yyyy");
  } catch {
    return value;
  }
}

function truncate(value: string | null | undefined, max = 80) {
  if (!value) return "—";
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

export function AdminDashboardClient() {
  const { canEdit, loading: authLoading, user } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>("visits");
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [records, setRecords] = useState<AdminRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setOffset(0);
    }, 300);
    return () => window.clearTimeout(timeoutId);
  }, [searchInput]);

  const fetchDashboardData = useCallback(async () => {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (search) params.set("search", search);

    const [summaryData, recordsData] = await Promise.all([
      api.get<AdminSummary>("/api/admin/summary"),
      api.get<AdminPaginated<AdminRecord>>(
        `${ADMIN_TAB_PATHS[activeTab]}?${params.toString()}`
      ),
    ]);

    return { summaryData, recordsData };
  }, [activeTab, offset, search]);

  useEffect(() => {
    if (authLoading || !canEdit) return;

    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError(null);
      setUnauthorized(false);
      try {
        const { summaryData, recordsData } = await fetchDashboardData();
        if (cancelled) return;
        setSummary(summaryData);
        setRecords(recordsData.records);
        setTotal(recordsData.meta.total);
      } catch (e) {
        if (cancelled) return;
        const message = e instanceof Error ? e.message : "Could not load admin data.";
        if (message.toLowerCase().includes("admin access")) {
          setUnauthorized(true);
        } else {
          setError(message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [authLoading, canEdit, fetchDashboardData]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnauthorized(false);
    try {
      const { summaryData, recordsData } = await fetchDashboardData();
      setSummary(summaryData);
      setRecords(recordsData.records);
      setTotal(recordsData.meta.total);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Could not load admin data.";
      if (message.toLowerCase().includes("admin access")) {
        setUnauthorized(true);
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchDashboardData]);

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil(total / PAGE_SIZE)),
    [total]
  );
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    setError(null);
    try {
      switch (deleteTarget.tab) {
        case "visits":
          await api.delete(`/api/visits/${deleteTarget.id}`);
          break;
        case "artworks":
          await api.delete(`/api/artworks/${deleteTarget.id}`);
          break;
        case "annotations":
          await api.delete(`/api/annotations/${deleteTarget.id}`);
          break;
        case "entities":
          await api.delete(`/api/cultural-entities/${deleteTarget.id}`);
          break;
        case "research-notes":
          await api.delete(
            `/api/artworks/${deleteTarget.artworkId}/research/${deleteTarget.id}`
          );
          break;
      }
      setDeleteTarget(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete record.");
    } finally {
      setDeleteLoading(false);
    }
  }

  if (authLoading) {
    return <p className="text-sm text-muted-foreground">Checking sign-in status…</p>;
  }

  if (!user || !canEdit) {
    return (
      <div className="mx-auto max-w-lg space-y-4 rounded-xl border border-border bg-card p-5">
        <div className="space-y-1">
          <h1 className="font-heading text-2xl">Admin dashboard</h1>
          <p className="text-sm text-muted-foreground">Sign in to manage CultureGraph.</p>
        </div>
        <GoogleSignInButton />
      </div>
    );
  }

  if (unauthorized) {
    return (
      <div className="mx-auto max-w-lg space-y-3 rounded-xl border border-border bg-card p-5">
        <h1 className="font-heading text-2xl">Admin dashboard</h1>
        <p className="text-sm text-destructive">
          This Google account is not authorized for admin access.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-10">
      <header className="space-y-1">
        <h1 className="font-heading text-2xl sm:text-3xl">Admin dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Browse database records for debugging, cleanup, and content management.
        </p>
      </header>

      {summary ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {(
            [
              ["visits", summary.visits],
              ["artworks", summary.artworks],
              ["annotations", summary.annotations],
              ["entities", summary.cultural_entities],
              ["research-notes", summary.research_notes],
            ] as const
          ).map(([tab, count]) => (
            <button
              key={tab}
              type="button"
              onClick={() => {
                setActiveTab(tab);
                setOffset(0);
              }}
              className={cn(
                "rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-muted/40",
                activeTab === tab && "ring-1 ring-foreground/15"
              )}
            >
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {ADMIN_TAB_LABELS[tab]}
              </p>
              <p className="mt-1 text-2xl font-medium tabular-nums">{count}</p>
            </button>
          ))}
        </div>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {(Object.keys(ADMIN_TAB_LABELS) as AdminTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => {
                setActiveTab(tab);
                setOffset(0);
              }}
              className={cn(
                "min-h-10 rounded-full border px-3 py-1.5 text-sm transition-colors",
                activeTab === tab
                  ? "border-foreground bg-foreground text-background"
                  : "border-border bg-background text-foreground hover:bg-muted"
              )}
            >
              {ADMIN_TAB_LABELS[tab]}
            </button>
          ))}
        </div>
        <Input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search records…"
          className="sm:max-w-xs"
          aria-label="Search admin records"
        />
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {loading ? <p className="text-sm text-muted-foreground">Loading…</p> : null}

      {!loading ? (
        <>
          <div className="hidden overflow-x-auto rounded-xl border border-border md:block">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-[0.12em] text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">ID</th>
                  {activeTab === "visits" ? (
                    <>
                      <th className="px-4 py-3 font-medium">Museum</th>
                      <th className="px-4 py-3 font-medium">City</th>
                      <th className="px-4 py-3 font-medium">Date</th>
                      <th className="px-4 py-3 font-medium">Notes</th>
                    </>
                  ) : null}
                  {activeTab === "artworks" ? (
                    <>
                      <th className="px-4 py-3 font-medium">Title</th>
                      <th className="px-4 py-3 font-medium">Artist</th>
                      <th className="px-4 py-3 font-medium">Visit</th>
                      <th className="px-4 py-3 font-medium">Image</th>
                    </>
                  ) : null}
                  {activeTab === "annotations" ? (
                    <>
                      <th className="px-4 py-3 font-medium">Artwork</th>
                      <th className="px-4 py-3 font-medium">Category</th>
                      <th className="px-4 py-3 font-medium">Text</th>
                    </>
                  ) : null}
                  {activeTab === "entities" ? (
                    <>
                      <th className="px-4 py-3 font-medium">Name</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 font-medium">Visit</th>
                    </>
                  ) : null}
                  {activeTab === "research-notes" ? (
                    <>
                      <th className="px-4 py-3 font-medium">Artwork</th>
                      <th className="px-4 py-3 font-medium">Summary</th>
                    </>
                  ) : null}
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {records.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                      No records found.
                    </td>
                  </tr>
                ) : (
                  records.map((record) => (
                    <AdminTableRow
                      key={`${activeTab}-${record.id}`}
                      tab={activeTab}
                      record={record}
                      onDelete={setDeleteTarget}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>

          <ul className="space-y-3 md:hidden">
            {records.length === 0 ? (
              <li className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                No records found.
              </li>
            ) : (
              records.map((record) => (
                <AdminMobileCard
                  key={`${activeTab}-${record.id}-mobile`}
                  tab={activeTab}
                  record={record}
                  onDelete={setDeleteTarget}
                />
              ))
            )}
          </ul>
        </>
      ) : null}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {total} record{total === 1 ? "" : "s"}
          {search ? ` matching “${search}”` : ""}
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={offset <= 0 || loading}
            onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {currentPage} of {pageCount}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={offset + PAGE_SIZE >= total || loading}
            onClick={() => setOffset((value) => value + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>

      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete record?"
        description={
          deleteTarget
            ? `Permanently delete “${deleteTarget.label}”? This cannot be undone.`
            : "Permanently delete this record?"
        }
        loading={deleteLoading}
        onConfirm={confirmDelete}
      />
    </div>
  );
}

function AdminTableRow({
  tab,
  record,
  onDelete,
}: {
  tab: AdminTab;
  record: AdminRecord;
  onDelete: (target: DeleteTarget) => void;
}) {
  const detailLink = getDetailLink(tab, record);
  const deleteTarget = getDeleteTarget(tab, record);

  return (
    <tr className="border-b border-border/70 last:border-b-0">
      <td className="px-4 py-3 tabular-nums">{record.id}</td>
      {tab === "visits" ? (
        <>
          <td className="px-4 py-3">{(record as AdminVisitRecord).museum_name}</td>
          <td className="px-4 py-3">{(record as AdminVisitRecord).city}</td>
          <td className="px-4 py-3">{(record as AdminVisitRecord).visit_date}</td>
          <td className="px-4 py-3">{truncate((record as AdminVisitRecord).notes)}</td>
        </>
      ) : null}
      {tab === "artworks" ? (
        <>
          <td className="px-4 py-3">{(record as AdminArtworkRecord).title}</td>
          <td className="px-4 py-3">{truncate((record as AdminArtworkRecord).artist, 40)}</td>
          <td className="px-4 py-3 tabular-nums">
            {(record as AdminArtworkRecord).visit_id ?? "—"}
          </td>
          <td className="px-4 py-3">
            {(record as AdminArtworkRecord).image_url ? "Yes" : "No"}
          </td>
        </>
      ) : null}
      {tab === "annotations" ? (
        <>
          <td className="px-4 py-3 tabular-nums">
            {(record as AdminAnnotationRecord).artwork_id}
          </td>
          <td className="px-4 py-3">{(record as AdminAnnotationRecord).category}</td>
          <td className="px-4 py-3">{truncate((record as AdminAnnotationRecord).text)}</td>
        </>
      ) : null}
      {tab === "entities" ? (
        <>
          <td className="px-4 py-3">{(record as AdminEntityRecord).name}</td>
          <td className="px-4 py-3">{(record as AdminEntityRecord).entity_type}</td>
          <td className="px-4 py-3 tabular-nums">{(record as AdminEntityRecord).visit_id}</td>
        </>
      ) : null}
      {tab === "research-notes" ? (
        <>
          <td className="px-4 py-3 tabular-nums">
            {(record as AdminResearchNoteRecord).artwork_id}
          </td>
          <td className="px-4 py-3">
            {truncate((record as AdminResearchNoteRecord).short_summary)}
          </td>
        </>
      ) : null}
      <td className="px-4 py-3">{formatDate(record.created_at)}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {detailLink ? (
            <Link
              href={detailLink}
              className="text-sm underline-offset-2 hover:underline"
            >
              View
            </Link>
          ) : null}
          {deleteTarget ? (
            <AdminActionsMenu onDelete={() => onDelete(deleteTarget)} />
          ) : null}
        </div>
      </td>
    </tr>
  );
}

function AdminMobileCard({
  tab,
  record,
  onDelete,
}: {
  tab: AdminTab;
  record: AdminRecord;
  onDelete: (target: DeleteTarget) => void;
}) {
  const detailLink = getDetailLink(tab, record);
  const deleteTarget = getDeleteTarget(tab, record);
  const title = getRecordTitle(tab, record);

  return (
    <li className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">#{record.id}</p>
          <p className="mt-1 text-base font-medium">{title}</p>
          <p className="mt-1 text-xs text-muted-foreground">{formatDate(record.created_at)}</p>
        </div>
        {deleteTarget ? <AdminActionsMenu onDelete={() => onDelete(deleteTarget)} /> : null}
      </div>
      {detailLink ? (
        <Link
          href={detailLink}
          className="mt-3 inline-flex min-h-10 items-center text-sm underline-offset-2 hover:underline"
        >
          View detail
        </Link>
      ) : null}
    </li>
  );
}

function getDetailLink(tab: AdminTab, record: AdminRecord): string | null {
  switch (tab) {
    case "visits":
      return `/visits/${record.id}`;
    case "artworks":
      return `/artworks/${record.id}`;
    case "annotations":
      return `/artworks/${(record as AdminAnnotationRecord).artwork_id}/annotate`;
    case "entities":
      return `/visits/${(record as AdminEntityRecord).visit_id}`;
    case "research-notes":
      return `/artworks/${(record as AdminResearchNoteRecord).artwork_id}`;
    default:
      return null;
  }
}

function getDeleteTarget(tab: AdminTab, record: AdminRecord): DeleteTarget | null {
  switch (tab) {
    case "visits":
      return {
        tab,
        id: record.id,
        label: (record as AdminVisitRecord).museum_name,
      };
    case "artworks":
      return {
        tab,
        id: record.id,
        label: (record as AdminArtworkRecord).title,
      };
    case "annotations":
      return {
        tab,
        id: record.id,
        label: truncate((record as AdminAnnotationRecord).text, 40),
      };
    case "entities":
      return {
        tab,
        id: record.id,
        label: (record as AdminEntityRecord).name,
      };
    case "research-notes":
      return {
        tab,
        id: record.id,
        artworkId: (record as AdminResearchNoteRecord).artwork_id,
        label: truncate((record as AdminResearchNoteRecord).short_summary, 40),
      };
    default:
      return null;
  }
}

function getRecordTitle(tab: AdminTab, record: AdminRecord): string {
  switch (tab) {
    case "visits":
      return (record as AdminVisitRecord).museum_name;
    case "artworks":
      return (record as AdminArtworkRecord).title;
    case "annotations":
      return truncate((record as AdminAnnotationRecord).text, 60);
    case "entities":
      return (record as AdminEntityRecord).name;
    case "research-notes":
      return truncate((record as AdminResearchNoteRecord).short_summary, 60);
    default:
      return String(record.id);
  }
}
