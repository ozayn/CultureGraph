"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { formatCalendarDate } from "@/lib/calendar-date";
import { Plus } from "lucide-react";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";
import { CulturalEntityForm } from "@/components/cultural-entities/cultural-entity-form";
import { AuthGate } from "@/components/auth/auth-gate";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ButtonLink } from "@/components/ui/button-link";
import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { VisitForm } from "@/components/visits/visit-form";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import {
  ENTITY_TYPE_ICONS,
  ENTITY_TYPE_LABELS,
  groupVisitDetailEntities,
} from "@/lib/entity-types";
import { artworkDisplayTitle } from "@/lib/artwork-metadata";
import { entityThumbnailUrl } from "@/lib/thumbnails";
import type { Artwork, CulturalEntity, Visit } from "@/lib/types";

interface VisitDetailClientProps {
  visit: Visit;
  artworks: Artwork[];
  culturalEntities: CulturalEntity[];
}

interface CulturalEntityCardProps {
  entity: CulturalEntity;
  canEdit: boolean;
  onEdit: (entity: CulturalEntity) => void;
  onDelete: (entity: CulturalEntity) => void;
}

interface ArtworkCardProps {
  artwork: Artwork;
  canEdit: boolean;
  onDelete: (artwork: Artwork) => void;
}

function ArtworkCard({ artwork, canEdit, onDelete }: ArtworkCardProps) {
  return (
    <li className="rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 p-4">
        <Link
          href={`/artworks/${artwork.id}`}
          className="flex min-h-11 min-w-0 flex-1 items-center gap-3 transition-colors active:opacity-80"
        >
          <EntryThumbnail
            artwork={artwork}
            imageKind="thumbnail"
            alt={artworkDisplayTitle(artwork.title)}
            entityType="artwork"
            size="md"
          />
          <div className="min-w-0 flex-1">
            <p className="text-base font-medium">{artworkDisplayTitle(artwork.title)}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {[artwork.artist, artwork.year_period].filter(Boolean).join(" · ")}
            </p>
          </div>
        </Link>
        {canEdit ? (
          <AdminActionsMenu
            label={`Actions for ${artworkDisplayTitle(artwork.title)}`}
            onDelete={() => onDelete(artwork)}
          />
        ) : null}
      </div>
    </li>
  );
}

function CulturalEntityCard({ entity, canEdit, onEdit, onDelete }: CulturalEntityCardProps) {
  const Icon = ENTITY_TYPE_ICONS[entity.entity_type];
  const tagLine = [
    ...entity.themes,
    ...entity.concepts,
    ...entity.movements,
    ...entity.historical_events,
  ]
    .filter(Boolean)
    .slice(0, 4);

  return (
    <li className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <EntryThumbnail
          imageUrl={entityThumbnailUrl(entity)}
          alt={entity.name}
          entityType={entity.entity_type}
          size="md"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground">
                <Icon className="size-3" strokeWidth={1.75} />
                {ENTITY_TYPE_LABELS[entity.entity_type]}
              </span>
            </div>
            {canEdit ? (
              <AdminActionsMenu
                label={`Actions for ${entity.name}`}
                onEdit={() => onEdit(entity)}
                onDelete={() => onDelete(entity)}
              />
            ) : null}
          </div>
          <p className="mt-2 text-base font-medium">{entity.name}</p>
          {entity.description ? (
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {entity.description}
            </p>
          ) : null}
          {entity.related_entities.length > 0 ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Related: {entity.related_entities.join(", ")}
            </p>
          ) : null}
          {tagLine.length > 0 ? (
            <p className="mt-2 text-xs text-muted-foreground">{tagLine.join(" · ")}</p>
          ) : null}
        </div>
      </div>
    </li>
  );
}

export function VisitDetailClient({
  visit: initialVisit,
  artworks,
  culturalEntities: initialCulturalEntities,
}: VisitDetailClientProps) {
  const router = useRouter();
  const [visit, setVisit] = useState(initialVisit);
  const [visitArtworks, setVisitArtworks] = useState(artworks);
  const [culturalEntities, setCulturalEntities] = useState(initialCulturalEntities);
  const [addOpen, setAddOpen] = useState(false);
  const [editVisitOpen, setEditVisitOpen] = useState(false);
  const [deleteVisitOpen, setDeleteVisitOpen] = useState(false);
  const [deleteVisitLoading, setDeleteVisitLoading] = useState(false);
  const [deleteVisitError, setDeleteVisitError] = useState<string | null>(null);
  const [editingEntity, setEditingEntity] = useState<CulturalEntity | null>(null);
  const [deletingEntity, setDeletingEntity] = useState<CulturalEntity | null>(null);
  const [deleteEntityLoading, setDeleteEntityLoading] = useState(false);
  const [deletingArtwork, setDeletingArtwork] = useState<Artwork | null>(null);
  const [deleteArtworkLoading, setDeleteArtworkLoading] = useState(false);
  const { canEdit } = useAuth();
  const groupedEntities = useMemo(
    () => groupVisitDetailEntities(culturalEntities),
    [culturalEntities]
  );

  async function deleteVisit() {
    setDeleteVisitLoading(true);
    setDeleteVisitError(null);
    try {
      await api.delete(`/api/visits/${visit.id}`);
      router.push("/visits");
      router.refresh();
    } catch (e) {
      setDeleteVisitError(e instanceof Error ? e.message : "Could not delete visit.");
      setDeleteVisitLoading(false);
    }
  }

  async function deleteEntity() {
    if (!deletingEntity) return;
    setDeleteEntityLoading(true);
    try {
      await api.delete(`/api/cultural-entities/${deletingEntity.id}`);
      setCulturalEntities((current) =>
        current.filter((entity) => entity.id !== deletingEntity.id)
      );
      setDeletingEntity(null);
      router.refresh();
    } catch (e) {
      setDeleteVisitError(e instanceof Error ? e.message : "Could not delete entity.");
    } finally {
      setDeleteEntityLoading(false);
    }
  }

  async function deleteArtwork() {
    if (!deletingArtwork) return;
    setDeleteArtworkLoading(true);
    setDeleteVisitError(null);
    try {
      await api.delete(`/api/artworks/${deletingArtwork.id}`);
      setVisitArtworks((current) =>
        current.filter((artwork) => artwork.id !== deletingArtwork.id)
      );
      setDeletingArtwork(null);
      router.refresh();
    } catch (e) {
      setDeleteVisitError(e instanceof Error ? e.message : "Could not delete artwork.");
    } finally {
      setDeleteArtworkLoading(false);
    }
  }

  return (
    <>
      <div className="space-y-6 pb-24 sm:space-y-8 sm:pb-10">
        <section className="space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {formatCalendarDate(visit.visit_date)} · {visit.city}
              </p>
              <h1 className="font-heading text-2xl font-normal sm:text-3xl">{visit.museum_name}</h1>
            </div>
            {canEdit ? (
              <AdminActionsMenu
                label="Visit actions"
                onEdit={() => setEditVisitOpen(true)}
                onDelete={() => setDeleteVisitOpen(true)}
              />
            ) : null}
          </div>
          {visit.notes ? (
            <p className="whitespace-pre-line text-base leading-relaxed text-muted-foreground">
              {visit.notes}
            </p>
          ) : null}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ButtonLink
                href="/visits"
                variant="ghost"
                size="sm"
                className="inline-flex min-h-11 sm:hidden"
              >
                All visits
              </ButtonLink>
              <h2 className="font-heading text-xl">Artworks</h2>
            </div>
            <ButtonLink href="/visits" variant="ghost" size="sm" className="hidden min-h-11 sm:inline-flex">
              All visits
            </ButtonLink>
          </div>

          {visitArtworks.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border px-4 py-10 text-center text-muted-foreground">
              No artworks yet. Tap Add artwork below.
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {visitArtworks.map((artwork) => (
                <ArtworkCard
                  key={artwork.id}
                  artwork={artwork}
                  canEdit={canEdit}
                  onDelete={setDeletingArtwork}
                />
              ))}
            </ul>
          )}
        </section>

        {groupedEntities.map(({ section, items }) => (
          <section key={section.id} className="space-y-3">
            <h2 className="font-heading text-xl">{section.label}</h2>
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {items.map((entity) => (
                <CulturalEntityCard
                  key={entity.id}
                  entity={entity}
                  canEdit={canEdit}
                  onEdit={setEditingEntity}
                  onDelete={setDeletingEntity}
                />
              ))}
            </ul>
          </section>
        ))}

        <section className="hidden rounded-xl border border-border bg-card p-5 md:block">
          <h3 className="mb-4 font-heading text-xl">Add artwork</h3>
          {canEdit ? (
            <ProgressiveArtworkForm visitId={visit.id} compact />
          ) : (
            <AuthGate />
          )}
        </section>
      </div>

      {canEdit ? (
        <div
          className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background p-3 md:hidden"
          style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
        >
          <button
            type="button"
            onClick={() => setAddOpen(true)}
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 text-base font-medium text-primary-foreground active:opacity-90"
          >
            <Plus className="size-5" />
            Add artwork
          </button>
        </div>
      ) : null}

      {canEdit ? (
        <>
          <BottomSheet
            open={addOpen}
            onOpenChange={setAddOpen}
            title="Add artwork"
            description="Photo first — AI enrichment starts on the artwork page."
            footer={null}
          >
            <ProgressiveArtworkForm
              visitId={visit.id}
              compact
              onComplete={() => {
                setAddOpen(false);
                router.refresh();
              }}
            />
          </BottomSheet>

          <BottomSheet
            open={editVisitOpen}
            onOpenChange={setEditVisitOpen}
            title="Edit visit"
            description="Update museum, date, or notes."
          >
            <VisitForm
              visit={visit}
              compact
              redirectOnSave={false}
              onSuccess={(updated) => {
                setVisit(updated);
                setEditVisitOpen(false);
                router.refresh();
              }}
            />
          </BottomSheet>

          <BottomSheet
            open={editingEntity !== null}
            onOpenChange={(open) => {
              if (!open) setEditingEntity(null);
            }}
            title="Edit entry"
            description="Update this imported cultural entity."
          >
            {editingEntity ? (
              <CulturalEntityForm
                entity={editingEntity}
                onCancel={() => setEditingEntity(null)}
                onSuccess={(updated) => {
                  setCulturalEntities((current) =>
                    current.map((entity) => (entity.id === updated.id ? updated : entity))
                  );
                  setEditingEntity(null);
                  router.refresh();
                }}
              />
            ) : null}
          </BottomSheet>
        </>
      ) : null}

      <ConfirmDeleteDialog
        open={deleteVisitOpen}
        onOpenChange={setDeleteVisitOpen}
        title="Delete visit?"
        description="This permanently removes the visit, its artworks, annotations, research notes, and imported entries. Uploaded images are removed from disk when possible."
        loading={deleteVisitLoading}
        onConfirm={deleteVisit}
      />

      <ConfirmDeleteDialog
        open={deletingEntity !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingEntity(null);
        }}
        title="Delete entry?"
        description={
          deletingEntity
            ? `Remove “${deletingEntity.name}” from this visit?`
            : "Remove this entry from the visit?"
        }
        loading={deleteEntityLoading}
        onConfirm={deleteEntity}
      />

      <ConfirmDeleteDialog
        open={deletingArtwork !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingArtwork(null);
        }}
        title="Delete artwork?"
        description="Delete this artwork? Its annotations and research notes may also be removed."
        loading={deleteArtworkLoading}
        onConfirm={deleteArtwork}
      />

      {deleteVisitError ? (
        <p
          className="fixed left-4 right-4 z-50 rounded-lg border border-destructive/30 bg-background px-3 py-2 text-sm text-destructive md:bottom-4"
          style={{ bottom: "max(6rem, calc(4.5rem + env(safe-area-inset-bottom)))" }}
        >
          {deleteVisitError}
        </p>
      ) : null}
    </>
  );
}
