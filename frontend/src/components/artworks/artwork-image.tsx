"use client";

import { ImageIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { displayImageUrl } from "@/lib/media-url";
import { cn } from "@/lib/utils";

interface ArtworkImageProps {
  imageUrl?: string | null;
  className?: string;
  imgClassName?: string;
  /** Shown when the image is missing or fails to load — never a broken icon. */
  fallback?: React.ReactNode;
}

export function ArtworkImagePlaceholder({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-48 w-full items-center justify-center bg-muted/40 text-muted-foreground",
        className
      )}
    >
      <ImageIcon className="size-10 opacity-40" strokeWidth={1.5} aria-hidden />
    </div>
  );
}

export function ArtworkImage({
  imageUrl,
  className,
  imgClassName,
  fallback,
}: ArtworkImageProps) {
  const [broken, setBroken] = useState(false);
  const src = displayImageUrl(imageUrl);

  useEffect(() => {
    setBroken(false);
  }, [imageUrl]);

  if (!src || broken) {
    return (
      <div className={className}>
        {fallback ?? <ArtworkImagePlaceholder className={imgClassName} />}
      </div>
    );
  }

  return (
    <div className={className}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        aria-hidden
        decoding="async"
        loading="eager"
        onError={() => setBroken(true)}
        className={cn("block w-full object-contain", imgClassName)}
      />
    </div>
  );
}
