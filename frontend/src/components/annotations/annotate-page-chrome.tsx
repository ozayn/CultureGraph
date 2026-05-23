"use client";

import { ButtonLink } from "@/components/ui/button-link";
import type { Artwork } from "@/lib/types";

interface AnnotatePageChromeProps {
  artwork: Artwork;
  children: React.ReactNode;
}

export function AnnotatePageChrome({ artwork, children }: AnnotatePageChromeProps) {
  return (
    <div className="space-y-5 pb-24 sm:pb-10">
      <section className="space-y-1">
        <p className="text-sm text-muted-foreground">Annotate</p>
        <h1 className="font-heading text-2xl font-normal leading-tight sm:text-3xl">
          {artwork.title}
        </h1>
        {artwork.artist ? (
          <p className="text-base text-muted-foreground">{artwork.artist}</p>
        ) : null}
      </section>

      {children}

      <div
        className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background p-3 md:hidden"
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        <ButtonLink href={`/artworks/${artwork.id}`} variant="outline" className="w-full">
          Done
        </ButtonLink>
      </div>
    </div>
  );
}
