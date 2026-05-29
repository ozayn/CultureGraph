"use client";

import { useMemo, useState } from "react";

import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { AdminClearMissingUploadsResponse, AdminUploadHealth } from "@/lib/admin-types";
import { cn } from "@/lib/utils";

interface UploadStorageHealthCardProps {
  health: AdminUploadHealth | null;
  loading?: boolean;
  error?: string | null;
  onHealthRefresh?: () => Promise<void>;
}

export function UploadStorageHealthCard({
  health,
  loading = false,
  error = null,
  onHealthRefresh,
}: UploadStorageHealthCardProps) {
  const [clearOpen, setClearOpen] = useState(false);
  const [clearLoading, setClearLoading] = useState(false);
  const [clearError, setClearError] = useState<string | null>(null);

  const affectedRecords = useMemo(() => {
    if (!health) return 0;
    if (health.missing_record_count > 0) {
      return health.missing_record_count;
    }
    return new Set(health.records.map((record) => `${record.record_type}:${record.record_id}`))
      .size;
  }, [health]);

  async function confirmClearMissing() {
    setClearLoading(true);
    setClearError(null);
    try {
      await api.post<AdminClearMissingUploadsResponse>("/api/admin/upload-health/clear-missing");
      setClearOpen(false);
      await onHealthRefresh?.();
    } catch (e) {
      setClearError(e instanceof Error ? e.message : "Could not clear missing upload references.");
    } finally {
      setClearLoading(false);
    }
  }

  return (
    <section
      className={cn(
        "rounded-xl border bg-card p-4",
        health && !health.persistent ? "border-amber-500/40" : "border-border"
      )}
      aria-labelledby="upload-storage-health-heading"
    >
      <h2 id="upload-storage-health-heading" className="font-heading text-lg">
        Upload storage
      </h2>

      {loading ? (
        <p className="mt-2 text-sm text-muted-foreground">Checking upload storage…</p>
      ) : null}

      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
      {clearError ? <p className="mt-2 text-sm text-destructive">{clearError}</p> : null}

      {health ? (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">upload_dir</dt>
            <dd className="mt-0.5 font-mono text-xs break-all">{health.upload_dir}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">storage_backend</dt>
            <dd className="mt-0.5 font-medium">{health.storage_backend}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">persistent</dt>
            <dd className="mt-0.5 font-medium">{health.persistent ? "true" : "false"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">missing_count</dt>
            <dd
              className={cn(
                "mt-0.5 font-medium tabular-nums",
                health.missing_count > 0 && "text-destructive"
              )}
            >
              {health.missing_count}
            </dd>
          </div>
        </dl>
      ) : null}

      {health && !health.persistent ? (
        <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm leading-relaxed text-amber-950 dark:text-amber-100">
          Uploads are not on a persistent volume. Files may be lost on redeploy. Mount a Railway
          volume at <span className="font-mono">/app/uploads</span> and set{" "}
          <span className="font-mono">UPLOAD_DIR=/app/uploads</span>.
        </p>
      ) : null}

      {health && health.missing_count > 0 ? (
        <div className="mt-3 space-y-3">
          <p className="text-sm text-muted-foreground">
            {health.missing_count} database path{health.missing_count === 1 ? "" : "s"} point to
            missing files on disk across {affectedRecords} record
            {affectedRecords === 1 ? "" : "s"}.
            {health.records.length > 0 ? (
              <>
                {" "}
                Example: {health.records[0].record_type} #{health.records[0].record_id} (
                {health.records[0].field}).
              </>
            ) : null}
          </p>
          <Button
            type="button"
            variant="outline"
            size="touch"
            onClick={() => setClearOpen(true)}
          >
            Clear missing file references
          </Button>
        </div>
      ) : null}

      <ConfirmDeleteDialog
        open={clearOpen}
        onOpenChange={setClearOpen}
        title="Clear missing file references?"
        description={`This will remove broken upload paths from ${affectedRecords} record${
          affectedRecords === 1 ? "" : "s"
        }. The artworks will remain.`}
        confirmLabel="Clear references"
        loading={clearLoading}
        onConfirm={confirmClearMissing}
      />
    </section>
  );
}
