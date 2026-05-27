"use client";

import { useEffect, useState } from "react";

import {
  artworkDisplaySrc,
  artworkThumbnailSrc,
  pickArtworkDisplayRaw,
  pickArtworkThumbnailRaw,
} from "@/lib/thumbnails";
import type { Artwork } from "@/lib/types";
import { getApiBase } from "@/lib/api-config";

interface ArtworkImageDebugProps {
  artwork: Artwork;
}

export function ArtworkImageDebug({ artwork }: ArtworkImageDebugProps) {
  const [thumbStatus, setThumbStatus] = useState<"idle" | "ok" | "error">("idle");
  const [displayStatus, setDisplayStatus] = useState<"idle" | "ok" | "error">("idle");

  const thumbRaw = pickArtworkThumbnailRaw(artwork);
  const displayRaw = pickArtworkDisplayRaw(artwork);
  const thumbResolved = artworkThumbnailSrc(artwork);
  const displayResolved = artworkDisplaySrc(artwork);

  useEffect(() => {
    setThumbStatus("idle");
    setDisplayStatus("idle");
  }, [thumbResolved, displayResolved]);

  if (process.env.NODE_ENV === "production") {
    return null;
  }

  return (
    <details className="rounded-lg border border-dashed border-amber-500/50 bg-amber-50/80 px-3 py-2 text-xs text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
      <summary className="cursor-pointer font-medium">Image URL debug (dev only)</summary>
      <dl className="mt-2 space-y-1.5 break-all font-mono">
        <div>
          <dt className="font-sans font-medium text-amber-900/80 dark:text-amber-200/80">
            API base
          </dt>
          <dd>{getApiBase()}</dd>
        </div>
        <div>
          <dt className="font-sans font-medium">image_url</dt>
          <dd>{artwork.image_url ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-sans font-medium">image_thumbnail_url</dt>
          <dd>{artwork.image_thumbnail_url ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-sans font-medium">catalog_image_url</dt>
          <dd>{artwork.catalog_image_url ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-sans font-medium">catalog_thumbnail_url</dt>
          <dd>{artwork.catalog_thumbnail_url ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-sans font-medium">thumbnail raw → resolved</dt>
          <dd>
            {thumbRaw ?? "—"}
            <br />
            → {thumbResolved ?? "—"} ({thumbStatus})
          </dd>
          {thumbResolved ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={thumbResolved}
              alt=""
              className="mt-1 size-12 rounded object-cover"
              onLoad={() => setThumbStatus("ok")}
              onError={() => setThumbStatus("error")}
            />
          ) : null}
        </div>
        <div>
          <dt className="font-sans font-medium">display raw → resolved</dt>
          <dd>
            {displayRaw ?? "—"}
            <br />
            → {displayResolved ?? "—"} ({displayStatus})
          </dd>
          {displayResolved ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={displayResolved}
              alt=""
              className="mt-1 max-h-24 rounded object-contain"
              onLoad={() => setDisplayStatus("ok")}
              onError={() => setDisplayStatus("error")}
            />
          ) : null}
        </div>
      </dl>
    </details>
  );
}
