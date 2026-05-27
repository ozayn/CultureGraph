"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ArtworkRegionSelector } from "@/components/artworks/artwork-region-selector";
import { MuseumAutocomplete } from "@/components/museums/museum-autocomplete";
import { CameraUpload } from "@/components/ui/camera-upload";
import { Button } from "@/components/ui/button";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PhotoCaptureDateSuggestion } from "@/components/artworks/photo-capture-date-suggestion";
import { api } from "@/lib/api";
import type { ArtworkImageRegion } from "@/lib/artwork-region";
import { prepareArtworkUploadFile } from "@/lib/prepare-artwork-upload";
import {
  logUploadError,
  mapUploadError,
  mapValidationUploadError,
  type FriendlyUploadError,
} from "@/lib/upload-errors";
import { validateArtworkUploadFile } from "@/lib/upload-validation";
import type { Artwork } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ProgressiveArtworkFormProps {
  visitId?: number;
  artwork?: Artwork;
  onComplete?: (artwork?: Artwork) => void;
  compact?: boolean;
  /** When true, navigate to artwork detail after draft save (edit mode). */
  redirectOnSave?: boolean;
  /** Mobile quick-add: return to visit after saving draft. */
  returnToVisitAfterDraft?: boolean;
  /** After create, open artwork detail with AI enrichment. */
  openEnrichmentAfterSave?: boolean;
}

export function ProgressiveArtworkForm({
  visitId,
  artwork,
  onComplete,
  compact,
  redirectOnSave = !artwork,
  returnToVisitAfterDraft = false,
  openEnrichmentAfterSave = Boolean(visitId && !artwork),
}: ProgressiveArtworkFormProps) {
  const router = useRouter();
  const isQuickCapture = Boolean(visitId && !artwork);
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<FriendlyUploadError | null>(null);
  const [title, setTitle] = useState(artwork?.title ?? "");
  const [artist, setArtist] = useState(artwork?.artist ?? "");
  const [yearPeriod, setYearPeriod] = useState(artwork?.year_period ?? "");
  const [museumGallery, setMuseumGallery] = useState(artwork?.museum_gallery ?? "");
  const [medium, setMedium] = useState(artwork?.medium ?? "");
  const [personalNotes, setPersonalNotes] = useState(artwork?.personal_notes ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [pendingRegion, setPendingRegion] = useState<ArtworkImageRegion | null>(null);
  const [regionOpen, setRegionOpen] = useState(false);
  const [savedArtwork, setSavedArtwork] = useState<Artwork | null>(null);
  const [lastAction, setLastAction] = useState<"draft" | "details" | null>(null);
  const previewUrl = useMemo(
    () => (photo ? URL.createObjectURL(photo) : null),
    [photo]
  );

  const canSaveDraft = isQuickCapture ? Boolean(photo) : Boolean(photo || title.trim() || artwork);
  const busy = loading || preparing;

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function clearPhoto() {
    setPhoto(null);
    setPendingRegion(null);
    setError(null);
  }

  async function applyPendingRegion(artworkId: number): Promise<Artwork> {
    if (!pendingRegion) {
      return api.get<Artwork>(`/api/artworks/${artworkId}`);
    }
    return api.patch<Artwork>(`/api/artworks/${artworkId}/image-region`, {
      x_percent: pendingRegion.x_percent,
      y_percent: pendingRegion.y_percent,
      width_percent: pendingRegion.width_percent,
      height_percent: pendingRegion.height_percent,
    });
  }

  async function preparePhotoForUpload(file: File) {
    setPreparing(true);
    try {
      return await prepareArtworkUploadFile(file);
    } finally {
      setPreparing(false);
    }
  }

  function finishAfterSave(saved: Artwork) {
    setSavedArtwork(saved);

    if (returnToVisitAfterDraft && visitId) {
      onComplete?.(saved);
      router.push(`/visits/${visitId}`);
      router.refresh();
      return;
    }

    if (!artwork && openEnrichmentAfterSave) {
      onComplete?.(saved);
      router.push(`/artworks/${saved.id}?enrich=1`);
      router.refresh();
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
  }

  async function saveArtwork(includeDetails: boolean) {
    if (!canSaveDraft) {
      setError({
        kind: "unknown",
        message: isQuickCapture
          ? "Add a photo to save a draft."
          : "Add a photo or title to continue.",
        canRetry: false,
      });
      return;
    }

    setLoading(true);
    setError(null);
    setLastAction(includeDetails ? "details" : "draft");

    const payload = {
      title: title.trim() || null,
      artist: includeDetails && artist.trim() ? artist.trim() : null,
      year_period: includeDetails && yearPeriod.trim() ? yearPeriod.trim() : null,
      medium:
        includeDetails && medium.trim()
          ? medium.trim()
          : artwork?.medium ?? null,
      museum_gallery: includeDetails && museumGallery.trim() ? museumGallery.trim() : null,
      personal_notes:
        includeDetails && personalNotes.trim()
          ? personalNotes.trim()
          : artwork?.personal_notes ?? null,
      visit_id: visitId ?? artwork?.visit_id ?? null,
    };

    try {
      let saved = artwork
        ? await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload)
        : await api.post<Artwork>("/api/artworks", payload);

      if (photo) {
        const validationMessage = validateArtworkUploadFile(photo);
        if (validationMessage) {
          setError(mapValidationUploadError(validationMessage));
          return;
        }
        const prepared = await preparePhotoForUpload(photo);
        try {
          saved = await api.upload<Artwork>(`/api/artworks/${saved.id}/image`, prepared.file, {
            captured_at: prepared.capturedAt ?? undefined,
          });
          if (pendingRegion) {
            saved = await applyPendingRegion(saved.id);
          }
        } catch (uploadError) {
          logUploadError("artwork image upload", uploadError);
          setError(mapUploadError(uploadError, "upload"));
          return;
        }
      }

      finishAfterSave(saved);
    } catch (saveError) {
      logUploadError("save artwork", saveError);
      setError(mapUploadError(saveError, "save"));
    } finally {
      setLoading(false);
    }
  }

  function retryLastSave() {
    if (lastAction === "details") {
      void saveArtwork(true);
    } else if (lastAction === "draft") {
      void saveArtwork(false);
    }
  }

  const footer = (
    <div className="flex flex-col gap-2">
      {error ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <p>{error.message}</p>
          {error.canRetry ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-2 min-h-9"
              disabled={busy}
              onClick={retryLastSave}
            >
              Try again
            </Button>
          ) : null}
        </div>
      ) : null}

      {step === 1 ? (
        <>
          <Button
            type="button"
            size="touch"
            className="w-full"
            data-testid="save-draft"
            disabled={busy || !canSaveDraft}
            onClick={() => void saveArtwork(false)}
          >
            {busy ? (preparing ? "Preparing photo…" : "Saving draft…") : "Save draft"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="w-full"
            disabled={busy}
            onClick={() => setStep(2)}
          >
            Add details first
          </Button>
        </>
      ) : (
        <>
          <Button
            type="button"
            size="touch"
            className="w-full"
            disabled={busy || !canSaveDraft}
            onClick={() => void saveArtwork(true)}
          >
            {busy ? (preparing ? "Preparing photo…" : "Saving…") : "Save with details"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="w-full"
            disabled={busy}
            onClick={() => setStep(1)}
          >
            Back
          </Button>
        </>
      )}
    </div>
  );

  return (
    <div
      className={cn(
        compact ? "space-y-3" : "space-y-4",
        isQuickCapture && "pb-28"
      )}
    >
      {!isQuickCapture ? (
        <p className="text-sm text-muted-foreground">
          Step {step} of 2 · {step === 1 ? "Photo & quick note" : "Details"}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          {step === 1
            ? "Snap the work now — AI helps identify it on the next screen."
            : "Optional details — AI enrichment runs after you save."}
        </p>
      )}

      {step === 1 ? (
        <div className="space-y-3">
          <CameraUpload
            variant={isQuickCapture ? "compact" : "default"}
            previewUrl={previewUrl}
            selectedFile={photo}
            disabled={busy}
            onRemove={photo ? clearPhoto : undefined}
            onSetArtworkArea={
              photo && previewUrl ? () => setRegionOpen(true) : undefined
            }
            artworkAreaSet={Boolean(pendingRegion)}
            onSelect={(file) => {
              const uploadError = validateArtworkUploadFile(file);
              if (uploadError) {
                setError(mapValidationUploadError(uploadError));
                setPhoto(null);
                return;
              }
              setError(null);
              setPendingRegion(null);
              setPhoto(file);
            }}
          />

          <div className="space-y-1.5">
            <Label htmlFor="artwork-title" className="sr-only">
              Title or quick note
            </Label>
            <Input
              id="artwork-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Title or quick note (optional)"
              className="min-h-11"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            AI identification and collection search start automatically after you save.
          </p>
          {photo && previewUrl ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="min-h-9 w-full justify-start"
              disabled={busy}
              onClick={() => setRegionOpen(true)}
            >
              {pendingRegion ? "Edit artwork area" : "Set artwork area"}
            </Button>
          ) : null}
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
          <div className="space-y-2">
            <Label htmlFor="artwork-medium">Medium</Label>
            <Input
              id="artwork-medium"
              value={medium}
              onChange={(event) => setMedium(event.target.value)}
              placeholder="Optional — e.g. Oil on canvas"
            />
          </div>
          <MuseumAutocomplete
            id="artwork-museum"
            label="Museum / gallery room"
            value={museumGallery}
            onValueChange={setMuseumGallery}
            placeholder="Optional — e.g. West Building"
          />
          <div className="space-y-2">
            <Label htmlFor="artwork-notes">Notes</Label>
            <Textarea
              id="artwork-notes"
              value={personalNotes}
              onChange={(event) => setPersonalNotes(event.target.value)}
              placeholder="Optional — impressions, wall text, etc."
              rows={3}
              className="min-h-[4.5rem] resize-y"
            />
          </div>
        </div>
      )}

      {savedArtwork && !redirectOnSave && !returnToVisitAfterDraft ? (
        <PhotoCaptureDateSuggestion
          artwork={savedArtwork}
          onDismiss={() => onComplete?.(savedArtwork)}
          onVisitUpdated={() => onComplete?.(savedArtwork)}
        />
      ) : null}

      {isQuickCapture ? (
        <div
          className="sticky bottom-0 -mx-4 border-t border-border bg-popover px-4 pt-3 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]"
          style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}
        >
          {footer}
        </div>
      ) : (
        <div className="flex flex-col gap-2 sm:flex-row">{footer}</div>
      )}

      {previewUrl ? (
        <BottomSheet
          open={regionOpen}
          onOpenChange={setRegionOpen}
          title="Select artwork area"
          description="Frame the work inside your photo. Optional — you can skip and set this later."
          footer={null}
        >
          <ArtworkRegionSelector
            imageUrl={previewUrl}
            initialRegion={pendingRegion}
            onSave={(region) => {
              setPendingRegion(region);
              setRegionOpen(false);
            }}
            onUseFullImage={() => {
              setPendingRegion(null);
              setRegionOpen(false);
            }}
            onSkip={() => setRegionOpen(false)}
          />
        </BottomSheet>
      ) : null}
    </div>
  );
}
