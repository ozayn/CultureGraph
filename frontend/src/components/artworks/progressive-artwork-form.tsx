"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { MuseumAutocomplete } from "@/components/museums/museum-autocomplete";
import { CameraUpload } from "@/components/ui/camera-upload";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArtworkRegionSheet } from "@/components/artworks/artwork-region-sheet";
import { PhotoCaptureDateSuggestion } from "@/components/artworks/photo-capture-date-suggestion";
import { api } from "@/lib/api";
import { validateArtworkUploadFile } from "@/lib/upload-validation";
import type { Artwork } from "@/lib/types";

interface ProgressiveArtworkFormProps {
  visitId?: number;
  artwork?: Artwork;
  onComplete?: (artwork?: Artwork) => void;
  compact?: boolean;
  redirectOnSave?: boolean;
}

export function ProgressiveArtworkForm({
  visitId,
  artwork,
  onComplete,
  compact,
  redirectOnSave = !artwork,
}: ProgressiveArtworkFormProps) {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState(artwork?.title ?? "");
  const [artist, setArtist] = useState(artwork?.artist ?? "");
  const [yearPeriod, setYearPeriod] = useState(artwork?.year_period ?? "");
  const [museumGallery, setMuseumGallery] = useState(artwork?.museum_gallery ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [savedArtwork, setSavedArtwork] = useState<Artwork | null>(null);
  const [regionArtwork, setRegionArtwork] = useState<Artwork | null>(null);
  const [pendingRedirectId, setPendingRedirectId] = useState<number | null>(null);
  const previewUrl = useMemo(
    () => (photo ? URL.createObjectURL(photo) : null),
    [photo]
  );

  const canSaveStepOne = Boolean(photo || title.trim() || artwork);

  function finishRegionFlow(updated?: Artwork) {
    const target = updated ?? regionArtwork;
    const redirectId = pendingRedirectId;
    setRegionArtwork(null);
    setPendingRedirectId(null);
    if (!target) return;
    setSavedArtwork(target);
    if (redirectId) {
      router.push(`/artworks/${target.id}`);
      router.refresh();
      return;
    }
    onComplete?.(target);
  }

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function saveArtwork(includeDetails: boolean) {
    if (!canSaveStepOne) {
      setError("Add a photo to capture this work, or enter a title.");
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      title: title.trim() || null,
      artist: includeDetails && artist.trim() ? artist.trim() : null,
      year_period: includeDetails && yearPeriod.trim() ? yearPeriod.trim() : null,
      medium: artwork?.medium ?? null,
      museum_gallery: includeDetails && museumGallery.trim() ? museumGallery.trim() : null,
      personal_notes: artwork?.personal_notes ?? null,
      visit_id: visitId ?? artwork?.visit_id ?? null,
    };

    if (photo) {
      const uploadError = validateArtworkUploadFile(photo);
      if (uploadError) {
        setError(uploadError);
        setLoading(false);
        return;
      }
    }

    try {
      let saved = artwork
        ? await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload)
        : await api.post<Artwork>("/api/artworks", payload);

      if (photo) {
        saved = await api.upload<Artwork>(`/api/artworks/${saved.id}/image`, photo);
      }

      setSavedArtwork(saved);

      if (photo && saved.image_url) {
        setRegionArtwork(saved);
        if (redirectOnSave) {
          setPendingRedirectId(saved.id);
        }
        return;
      }

      if (redirectOnSave) {
        router.push(`/artworks/${saved.id}`);
        router.refresh();
        return;
      }

      if (saved.captured_date_source !== "exif" || !saved.captured_at) {
        onComplete?.(saved);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save artwork.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={compact ? "space-y-4" : "space-y-5"}>
      <p className="text-sm text-muted-foreground">
        Step {step} of 2 · {step === 1 ? "Photo & quick note" : "Optional details"}
      </p>

      {step === 1 ? (
        <div className="space-y-4">
          <CameraUpload
            previewUrl={previewUrl}
            selectedFile={photo}
            error={error}
            disabled={loading}
            onSelect={(file) => {
              const uploadError = validateArtworkUploadFile(file);
              if (uploadError) {
                setError(uploadError);
                setPhoto(null);
                return;
              }
              setError(null);
              setPhoto(file);
            }}
          />

          <div className="space-y-2">
            <Label htmlFor="artwork-title">Title or quick note</Label>
            <p className="text-xs text-muted-foreground">
              Optional — you can identify it later.
            </p>
            <Input
              id="artwork-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. dancer studies, north gallery"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="artwork-artist">Artist</Label>
            <Input
              id="artwork-artist"
              value={artist}
              onChange={(event) => setArtist(event.target.value)}
              placeholder="Optional"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="artwork-year">Year / period</Label>
            <Input
              id="artwork-year"
              value={yearPeriod}
              onChange={(event) => setYearPeriod(event.target.value)}
              placeholder="Optional"
            />
          </div>
          <MuseumAutocomplete
            id="artwork-museum"
            label="Museum / gallery"
            value={museumGallery}
            onValueChange={setMuseumGallery}
            placeholder="Optional — e.g. West Building"
          />
        </div>
      )}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {savedArtwork && !redirectOnSave && !regionArtwork ? (
        <PhotoCaptureDateSuggestion
          artwork={savedArtwork}
          onDismiss={() => onComplete?.(savedArtwork)}
          onVisitUpdated={() => onComplete?.(savedArtwork)}
        />
      ) : null}

      {regionArtwork ? (
        <ArtworkRegionSheet
          open
          artwork={regionArtwork}
          onOpenChange={(open) => {
            if (!open) finishRegionFlow();
          }}
          onSaved={(updated) => finishRegionFlow(updated)}
        />
      ) : null}

      <div className="flex flex-col gap-2 sm:flex-row">
        {step === 2 ? (
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="sm:flex-1"
            disabled={loading}
            onClick={() => setStep(1)}
          >
            Back
          </Button>
        ) : null}

        {step === 1 ? (
          <>
            <Button
              type="button"
              size="touch"
              className="sm:flex-1"
              disabled={loading || !canSaveStepOne}
              onClick={() => setStep(2)}
            >
              Add details
            </Button>
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="sm:flex-1"
              disabled={loading || !canSaveStepOne}
              onClick={() => saveArtwork(false)}
            >
              {loading ? "Saving…" : "Save now"}
            </Button>
          </>
        ) : (
          <>
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="sm:flex-1"
              disabled={loading}
              onClick={() => saveArtwork(false)}
            >
              Skip details
            </Button>
            <Button
              type="button"
              size="touch"
              className="sm:flex-1"
              disabled={loading}
              onClick={() => saveArtwork(true)}
            >
              {loading ? "Saving…" : "Save artwork"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
