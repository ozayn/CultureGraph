"use client";

import { useMemo, useState } from "react";
import { Loader2, Tag, Trash2 } from "lucide-react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { Button } from "@/components/ui/button";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { CameraUpload } from "@/components/ui/camera-upload";
import { api } from "@/lib/api";
import {
  artworkDisplayTitle,
  extractLabelMetadataHints,
  formatMetadataCurrent,
  isPlaceholderTitle,
} from "@/lib/artwork-metadata";
import { prepareArtworkUploadFile } from "@/lib/prepare-artwork-upload";
import { validateArtworkUploadFile } from "@/lib/upload-validation";
import { resolveImageUrl } from "@/lib/media-url";
import type { Artwork } from "@/lib/types";

interface ArtworkLabelSectionProps {
  artwork: Artwork;
  canEdit: boolean;
  onArtworkUpdated: (artwork: Artwork) => void;
}

export function ArtworkLabelSection({
  artwork,
  canEdit,
  onArtworkUpdated,
}: ArtworkLabelSectionProps) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [labelFile, setLabelFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyTitle, setApplyTitle] = useState(true);
  const [applyArtist, setApplyArtist] = useState(true);

  const hasLabel = Boolean(artwork.label_image_url);
  const labelThumb = artwork.label_image_thumbnail_url ?? artwork.label_image_url;
  const labelHints = useMemo(
    () => extractLabelMetadataHints(artwork.label_ocr_text),
    [artwork.label_ocr_text]
  );

  async function uploadLabel() {
    if (!labelFile) return;
    const validationError = validateArtworkUploadFile(labelFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const prepared = await prepareArtworkUploadFile(labelFile);
      const updated = await api.upload<Artwork>(
        `/api/artworks/${artwork.id}/label-image`,
        prepared.file
      );
      onArtworkUpdated(updated);
      setSheetOpen(false);
      setLabelFile(null);
      setPreviewUrl(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not upload label photo.");
    } finally {
      setUploading(false);
    }
  }

  async function deleteLabel() {
    setDeleting(true);
    setError(null);
    try {
      const updated = await api.delete<Artwork>(`/api/artworks/${artwork.id}/label-image`);
      onArtworkUpdated(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove label photo.");
    } finally {
      setDeleting(false);
    }
  }

  async function applyLabelMetadata() {
    if (!labelHints) return;
    setSavingMetadata(true);
    setError(null);
    try {
      const payload: Partial<Artwork> = {};
      if (applyTitle && labelHints.title) payload.title = labelHints.title;
      if (applyArtist && labelHints.artist) payload.artist = labelHints.artist;
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onArtworkUpdated(updated);
      setReviewOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save label metadata.");
    } finally {
      setSavingMetadata(false);
    }
  }

  function openReview() {
    setApplyTitle(Boolean(labelHints?.title) && isPlaceholderTitle(artwork.title));
    setApplyArtist(Boolean(labelHints?.artist));
    setReviewOpen(true);
  }

  return (
    <section className="rounded-xl border border-border bg-card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Tag className="size-4" aria-hidden />
          </div>
          <div>
            <h3 className="font-heading text-lg">Museum label</h3>
            <p className="text-sm text-muted-foreground">
              Upload the wall label or info card for more reliable title and artist hints.
            </p>
          </div>
        </div>
        {canEdit ? (
          <Button type="button" variant="outline" size="sm" className="min-h-9 shrink-0" onClick={() => setSheetOpen(true)}>
            {hasLabel ? "Replace label" : "Add label photo"}
          </Button>
        ) : null}
      </div>

      {hasLabel ? (
        <div className="mt-4 space-y-3">
          <div className="flex gap-3">
            <EntryThumbnail
              imageUrl={labelThumb ? resolveImageUrl(labelThumb) : null}
              alt="Museum label"
              className="size-20 shrink-0 rounded-md"
            />
            <div className="min-w-0 flex-1 space-y-2 text-sm">
              {artwork.label_uploaded_at ? (
                <p className="text-xs text-muted-foreground">
                  Uploaded {new Date(artwork.label_uploaded_at).toLocaleString()}
                </p>
              ) : null}
              {artwork.label_ocr_text ? (
                <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-lg border border-border/80 bg-muted/20 p-3 text-xs leading-relaxed text-foreground">
                  {artwork.label_ocr_text}
                </pre>
              ) : (
                <p className="text-muted-foreground">
                  Label photo saved. OCR text will appear after processing or AI enrichment.
                </p>
              )}
            </div>
          </div>

          {canEdit && labelHints && (labelHints.title || labelHints.artist) ? (
            <Button type="button" variant="secondary" size="sm" className="min-h-9" onClick={openReview}>
              Use label metadata
            </Button>
          ) : null}

          {canEdit ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="min-h-9 text-destructive hover:text-destructive"
              disabled={deleting}
              onClick={() => void deleteLabel()}
            >
              {deleting ? (
                <>
                  <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                  Removing…
                </>
              ) : (
                <>
                  <Trash2 className="mr-1.5 size-3.5" />
                  Remove label photo
                </>
              )}
            </Button>
          ) : null}
        </div>
      ) : canEdit ? (
        <p className="mt-3 text-sm text-muted-foreground">
          No label photo yet. Capture the placard next to the artwork for better identification.
        </p>
      ) : null}

      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}

      {canEdit ? (
        <>
          <BottomSheet
            open={sheetOpen}
            onOpenChange={setSheetOpen}
            title={hasLabel ? "Replace label photo" : "Add label photo"}
            description="Photograph the museum wall label or information card beside the artwork."
          >
            <div className="space-y-4 pb-2">
              <CameraUpload
                previewUrl={previewUrl}
                selectedFile={labelFile}
                disabled={uploading}
                error={error}
                onSelect={(file) => {
                  const validationError = validateArtworkUploadFile(file);
                  if (validationError) {
                    setError(validationError);
                    setLabelFile(null);
                    setPreviewUrl(null);
                    return;
                  }
                  setError(null);
                  setLabelFile(file);
                  setPreviewUrl(URL.createObjectURL(file));
                }}
              />
              <Button
                type="button"
                size="touch"
                className="w-full"
                disabled={uploading || !labelFile}
                onClick={() => void uploadLabel()}
              >
                {uploading ? "Uploading…" : "Upload label photo"}
              </Button>
            </div>
          </BottomSheet>

          <BottomSheet
            open={reviewOpen}
            onOpenChange={setReviewOpen}
            title="Use label metadata"
            description="Review extracted label text before saving to the artwork record."
          >
            <div className="space-y-4 pb-2 text-sm">
              {labelHints?.title ? (
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={applyTitle}
                    onChange={(event) => setApplyTitle(event.target.checked)}
                  />
                  <span>
                    <span className="block text-xs uppercase tracking-[0.12em] text-muted-foreground">
                      Title
                    </span>
                    <span className="block">{labelHints.title}</span>
                    <span className="text-xs text-muted-foreground">
                      Current: {artworkDisplayTitle(artwork.title)}
                    </span>
                  </span>
                </label>
              ) : null}
              {labelHints?.artist ? (
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={applyArtist}
                    onChange={(event) => setApplyArtist(event.target.checked)}
                  />
                  <span>
                    <span className="block text-xs uppercase tracking-[0.12em] text-muted-foreground">
                      Artist
                    </span>
                    <span className="block">{labelHints.artist}</span>
                    <span className="text-xs text-muted-foreground">
                      Current: {formatMetadataCurrent(artwork.artist, "Unknown")}
                    </span>
                  </span>
                </label>
              ) : null}
              <Button
                type="button"
                size="touch"
                className="w-full"
                disabled={savingMetadata || (!applyTitle && !applyArtist)}
                onClick={() => void applyLabelMetadata()}
              >
                {savingMetadata ? "Saving…" : "Save selected fields"}
              </Button>
            </div>
          </BottomSheet>
        </>
      ) : null}
    </section>
  );
}
