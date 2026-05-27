"use client";

import { useEffect, useState } from "react";

import { ENTITY_TYPE_ICONS, ENTITY_TYPE_LABELS } from "@/lib/entity-types";
import { thumbnailDisplayUrl } from "@/lib/media-url";
import {
  resolveArtworkImageUrl,
  type ArtworkImageFields,
  type ThumbnailEntityType,
} from "@/lib/thumbnails";
import { cn } from "@/lib/utils";

export type EntryThumbnailSize = "sm" | "md" | "lg";

const SIZE_CLASSES: Record<EntryThumbnailSize, string> = {
  sm: "size-10",
  md: "size-12",
  lg: "size-16",
};

const ICON_CLASSES: Record<EntryThumbnailSize, string> = {
  sm: "size-4",
  md: "size-5",
  lg: "size-6",
};

interface EntryThumbnailProps {
  /** Raw path/URL (entities, import drafts). */
  imageUrl?: string | null;
  /** Prefer for artworks — applies field precedence and API base resolution. */
  artwork?: ArtworkImageFields;
  imageKind?: "thumbnail" | "detail";
  alt?: string;
  entityType?: ThumbnailEntityType;
  size?: EntryThumbnailSize;
  className?: string;
}

export function EntryThumbnail({
  imageUrl,
  artwork,
  imageKind = "thumbnail",
  alt,
  entityType = "artwork",
  size = "md",
  className,
}: EntryThumbnailProps) {
  const [broken, setBroken] = useState(false);
  const src = artwork
    ? resolveArtworkImageUrl(artwork, imageKind)
    : thumbnailDisplayUrl(imageUrl);
  const Icon = ENTITY_TYPE_ICONS[entityType];
  const typeLabel = ENTITY_TYPE_LABELS[entityType];
  const sizeClass = SIZE_CLASSES[size];
  const iconClass = ICON_CLASSES[size];
  const label = alt?.trim() || typeLabel;

  useEffect(() => {
    setBroken(false);
  }, [imageUrl, artwork, imageKind]);

  if (src && !broken) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        aria-hidden
        decoding="async"
        loading="lazy"
        onError={() => setBroken(true)}
        className={cn(
          sizeClass,
          "aspect-square shrink-0 overflow-hidden rounded-md object-cover ring-1 ring-border",
          className
        )}
      />
    );
  }

  return (
    <div
      role="img"
      aria-label={label}
      className={cn(
        sizeClass,
        "flex aspect-square shrink-0 items-center justify-center overflow-hidden rounded-md bg-muted ring-1 ring-border",
        className
      )}
    >
      <Icon className={cn(iconClass, "text-muted-foreground")} strokeWidth={1.75} />
    </div>
  );
}
