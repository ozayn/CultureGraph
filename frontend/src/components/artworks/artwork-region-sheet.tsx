"use client";

import { useState } from "react";

import { ArtworkRegionSelector } from "@/components/artworks/artwork-region-selector";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { api } from "@/lib/api";
import { artworkRegionFromArtwork, artworkSourceImageUrl, type ArtworkImageRegion } from "@/lib/artwork-region";
import type { Artwork } from "@/lib/types";

interface ArtworkRegionSheetProps {
  open: boolean;
  artwork: Artwork;
  onOpenChange: (open: boolean) => void;
  onSaved: (artwork: Artwork) => void;
}

export function ArtworkRegionSheet({
  open,
  artwork,
  onOpenChange,
  onSaved,
}: ArtworkRegionSheetProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sourceUrl = artworkSourceImageUrl(artwork);

  async function applyRegion(payload: Record<string, unknown>) {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.patch<Artwork>(
        `/api/artworks/${artwork.id}/image-region`,
        payload
      );
      onSaved(updated);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save artwork region.");
    } finally {
      setSaving(false);
    }
  }

  function saveRegion(region: ArtworkImageRegion) {
    void applyRegion({
      x_percent: region.x_percent,
      y_percent: region.y_percent,
      width_percent: region.width_percent,
      height_percent: region.height_percent,
    });
  }

  return (
    <BottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title="Select the artwork area"
      description="Frame the artwork inside your photo. Thumbnails, AI vision, and exact artwork search use this cropped region."
    >
      {sourceUrl ? (
        <ArtworkRegionSelector
          imageUrl={sourceUrl}
          initialRegion={artworkRegionFromArtwork(artwork)}
          saving={saving}
          onSave={saveRegion}
          onUseFullImage={() => void applyRegion({ use_full_image: true })}
          onSkip={() => onOpenChange(false)}
        />
      ) : (
        <p className="text-sm text-muted-foreground">Upload a photo first.</p>
      )}
      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
    </BottomSheet>
  );
}
