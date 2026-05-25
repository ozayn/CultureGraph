"use client";

import { ENTITY_TYPE_ICONS, ENTITY_TYPE_LABELS } from "@/lib/entity-types";
import { mediaUrl } from "@/lib/api";
import type { ThumbnailEntityType } from "@/lib/thumbnails";
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
  imageUrl?: string | null;
  alt?: string;
  entityType?: ThumbnailEntityType;
  size?: EntryThumbnailSize;
  className?: string;
}

export function EntryThumbnail({
  imageUrl,
  alt,
  entityType = "artwork",
  size = "md",
  className,
}: EntryThumbnailProps) {
  const resolvedUrl = mediaUrl(imageUrl);
  const Icon = ENTITY_TYPE_ICONS[entityType];
  const typeLabel = ENTITY_TYPE_LABELS[entityType];
  const sizeClass = SIZE_CLASSES[size];
  const iconClass = ICON_CLASSES[size];

  if (resolvedUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={resolvedUrl}
        alt={alt?.trim() || typeLabel}
        className={cn(
          sizeClass,
          "aspect-square shrink-0 rounded-md object-cover ring-1 ring-border",
          className
        )}
      />
    );
  }

  return (
    <div
      aria-hidden={alt ? undefined : true}
      className={cn(
        sizeClass,
        "flex aspect-square shrink-0 items-center justify-center rounded-md bg-muted ring-1 ring-border",
        className
      )}
    >
      <Icon className={cn(iconClass, "text-muted-foreground")} strokeWidth={1.75} />
      <span className="sr-only">{typeLabel}</span>
    </div>
  );
}
