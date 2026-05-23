"use client";

import Link from "next/link";
import { useState } from "react";
import { format } from "date-fns";
import { Plus } from "lucide-react";

import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ButtonLink } from "@/components/ui/button-link";
import type { Artwork, Visit } from "@/lib/types";

interface VisitDetailClientProps {
  visit: Visit;
  artworks: Artwork[];
}

export function VisitDetailClient({ visit, artworks }: VisitDetailClientProps) {
  const [addOpen, setAddOpen] = useState(false);

  return (
  <>
    <div className="space-y-6 pb-24 sm:space-y-8 sm:pb-10">
      <section className="space-y-2">
        <p className="text-sm text-muted-foreground">
          {format(new Date(visit.visit_date), "MMMM d, yyyy")} · {visit.city}
        </p>
        <h1 className="font-heading text-2xl font-normal sm:text-3xl">{visit.museum_name}</h1>
        {visit.notes ? (
          <p className="text-base leading-relaxed text-muted-foreground">{visit.notes}</p>
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

      <section className="hidden rounded-xl border border-border bg-card p-5 md:block">
        <h3 className="mb-4 font-heading text-xl">Add artwork</h3>
        <ProgressiveArtworkForm visitId={visit.id} compact />
      </section>
    </div>

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
  </>
  );
}
