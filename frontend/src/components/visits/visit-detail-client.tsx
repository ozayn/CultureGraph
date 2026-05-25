"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { format } from "date-fns";
import { Plus } from "lucide-react";

import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";
import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ButtonLink } from "@/components/ui/button-link";
import { useAuth } from "@/contexts/auth-context";
import {
  ENTITY_TYPE_ICONS,
  ENTITY_TYPE_LABELS,
  groupVisitDetailEntities,
} from "@/lib/entity-types";
import type { Artwork, CulturalEntity, Visit } from "@/lib/types";

interface VisitDetailClientProps {
  visit: Visit;
  artworks: Artwork[];
  culturalEntities: CulturalEntity[];
}

function CulturalEntityCard({ entity }: { entity: CulturalEntity }) {
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
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground">
          <Icon className="size-3" strokeWidth={1.75} />
          {ENTITY_TYPE_LABELS[entity.entity_type]}
        </span>
      </div>
      <p className="mt-2 text-base font-medium">{entity.name}</p>
      {entity.description ? (
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{entity.description}</p>
      ) : null}
      {entity.related_entities.length > 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Related: {entity.related_entities.join(", ")}
        </p>
      ) : null}
      {tagLine.length > 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">{tagLine.join(" · ")}</p>
      ) : null}
    </li>
  );
}

export function VisitDetailClient({
  visit,
  artworks,
  culturalEntities,
}: VisitDetailClientProps) {
  const [addOpen, setAddOpen] = useState(false);
  const { canEdit } = useAuth();
  const groupedEntities = useMemo(
    () => groupVisitDetailEntities(culturalEntities),
    [culturalEntities]
  );

  return (
    <>
      <div className="space-y-6 pb-24 sm:space-y-8 sm:pb-10">
        <section className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {format(new Date(visit.visit_date), "MMMM d, yyyy")} · {visit.city}
          </p>
          <h1 className="font-heading text-2xl font-normal sm:text-3xl">{visit.museum_name}</h1>
          {visit.notes ? (
            <p className="whitespace-pre-line text-base leading-relaxed text-muted-foreground">
              {visit.notes}
            </p>
          ) : null}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-heading text-xl">Artworks</h2>
            <ButtonLink href="/visits" variant="ghost" size="sm" className="hidden sm:inline-flex">
              All visits
            </ButtonLink>
          </div>

          {artworks.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border px-4 py-10 text-center text-muted-foreground">
              No artworks yet. Tap Add artwork below.
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {artworks.map((artwork) => (
                <li key={artwork.id}>
                  <Link
                    href={`/artworks/${artwork.id}`}
                    className="block min-h-11 rounded-xl border border-border bg-card p-4 transition-colors active:bg-muted/50"
                  >
                    <p className="text-base font-medium">{artwork.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {[artwork.artist, artwork.year_period].filter(Boolean).join(" · ")}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {groupedEntities.map(({ section, items }) => (
          <section key={section.id} className="space-y-3">
            <h2 className="font-heading text-xl">{section.label}</h2>
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {items.map((entity) => (
                <CulturalEntityCard key={entity.id} entity={entity} />
              ))}
            </ul>
          </section>
        ))}

        <section className="hidden rounded-xl border border-border bg-card p-5 md:block">
          <h3 className="mb-4 font-heading text-xl">Add artwork</h3>
          {canEdit ? (
            <ProgressiveArtworkForm visitId={visit.id} compact />
          ) : (
            <SignInPrompt compact />
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
        <BottomSheet
          open={addOpen}
          onOpenChange={setAddOpen}
          title="Add artwork"
          description="Start with a title and photo — details can wait."
        >
          <ProgressiveArtworkForm
            visitId={visit.id}
            compact
            onComplete={() => setAddOpen(false)}
          />
        </BottomSheet>
      ) : null}
    </>
  );
}
