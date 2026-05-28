"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Camera, ImageIcon, MapPin, Pencil, Sparkles } from "lucide-react";
import { useRef, useState, useMemo, useEffect } from "react";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { AnnotationDetailSheet } from "@/components/annotations/annotation-detail-sheet";
import { AnnotationOverviewList } from "@/components/annotations/annotation-overview-list";
import {
  ArtworkImageLookupAction,
  ArtworkImageLookupDebug,
  ArtworkImageLookupPanel,
  useArtworkImageLookup,
} from "@/components/artworks/artwork-image-lookup-panel";
import { AuthGate } from "@/components/auth/auth-gate";
import { SignInInlineHint } from "@/components/auth/sign-in-inline-hint";
import { ArtworkRegionSheet } from "@/components/artworks/artwork-region-sheet";
import { ArtworkImageDebug } from "@/components/artworks/artwork-image-debug";
import { ArtworkImage, ArtworkImagePlaceholder } from "@/components/artworks/artwork-image";
import { PhotoCaptureDateSuggestion } from "@/components/artworks/photo-capture-date-suggestion";
import { ArtworkEnrichmentPanel } from "@/components/artworks/artwork-enrichment-panel";
import { ArtworkLabelSection } from "@/components/artworks/artwork-label-section";
import { ResearchPanel } from "@/components/artworks/research-panel";
import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ButtonLink } from "@/components/ui/button-link";
import { Button } from "@/components/ui/button";
import { CameraUpload } from "@/components/ui/camera-upload";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { resolveArtworkImageRaw, resolveArtworkImageUrl } from "@/lib/thumbnails";
import { artworkDisplayTitle, extractLabelMetadataHints } from "@/lib/artwork-metadata";
import { artworkHasImageRegion } from "@/lib/artwork-region";
import { useAuth } from "@/contexts/auth-context";
import { formValuesToAnnotationPayload, type AnnotationPinFormValues } from "@/lib/annotation-form";
import { buildAnnotationTagSuggestions } from "@/lib/annotation-suggestions";
import type { ResearchMetadataHints } from "@/lib/artwork-metadata";
import { splitAnnotationsByPlacement } from "@/lib/annotation-placement";
import { setPendingAnnotationPlacement } from "@/lib/pending-annotation-placement";
import { validateArtworkUploadFile } from "@/lib/upload-validation";
import { prepareArtworkUploadFile } from "@/lib/prepare-artwork-upload";
import {
  type Annotation,
  type Artwork,
  type CulturalEntity,
} from "@/lib/types";

interface ArtworkDetailClientProps {
  artwork: Artwork;
  annotations: Annotation[];
  culturalEntities?: CulturalEntity[];
  autoEnrich?: boolean;
}

export function ArtworkDetailClient({
  artwork: initialArtwork,
  annotations: initialAnnotations,
  culturalEntities = [],
  autoEnrich = false,
}: ArtworkDetailClientProps) {
  const router = useRouter();
  const { canEdit, loading: authLoading } = useAuth();
  const researchRef = useRef<HTMLDivElement>(null);
  const enrichmentRef = useRef<HTMLDivElement>(null);
  const generateResearchRef = useRef<(() => Promise<void>) | null>(null);
  const [artwork, setArtwork] = useState(initialArtwork);
  const [annotations, setAnnotations] = useState(initialAnnotations);
  const [noteOpen, setNoteOpen] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [regionOpen, setRegionOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [deletingAnnotation, setDeletingAnnotation] = useState<Annotation | null>(null);
  const [deleteAnnotationLoading, setDeleteAnnotationLoading] = useState(false);
  const [savingAnnotation, setSavingAnnotation] = useState(false);
  const [annotationSuccess, setAnnotationSuccess] = useState<string | null>(null);

  const tagSuggestions = useMemo(
    () => buildAnnotationTagSuggestions(culturalEntities),
    [culturalEntities]
  );
  const { placed: placedAnnotations, unplaced: unplacedAnnotations } = useMemo(
    () => splitAnnotationsByPlacement(annotations),
    [annotations]
  );
  const [note, setNote] = useState(artwork.personal_notes ?? "");
  const [savingNote, setSavingNote] = useState(false);
  const [photoMode, setPhotoMode] = useState<"artwork" | "label">("artwork");
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadingLabel, setUploadingLabel] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const displayRaw = useMemo(() => resolveArtworkImageRaw(artwork, "detail"), [artwork]);
  const resolvedDisplayUrl = useMemo(
    () => resolveArtworkImageUrl(artwork, "detail"),
    [artwork]
  );
  const hasImage = Boolean(displayRaw);
  const labelLookupHints = useMemo(
    () => extractLabelMetadataHints(artwork.label_ocr_text),
    [artwork.label_ocr_text]
  );

  const openApplyReviewRef = useRef<(() => void) | null>(null);
  const [researchHints, setResearchHints] = useState<ResearchMetadataHints | null>(null);

  function scrollToEnrichment() {
    enrichmentRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  useEffect(() => {
    if (autoEnrich) {
      scrollToEnrichment();
    }
  }, [autoEnrich]);

  function handleArtworkUpdated(updated: Artwork) {
    setArtwork(updated);
    router.refresh();
  }

  function handleLookupApplied(updated: Artwork) {
    setArtwork(updated);
    router.refresh();
  }

  function handleRegionSaved(updated: Artwork) {
    setArtwork(updated);
    router.refresh();
  }

  async function saveNote() {
    setSavingNote(true);
    setError(null);
    try {
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, {
        personal_notes: note.trim() || null,
      });
      setArtwork(updated);
      setNoteOpen(false);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save note.");
    } finally {
      setSavingNote(false);
    }
  }

  async function uploadPhoto() {
    if (!photo) return;

    const uploadError = validateArtworkUploadFile(photo);
    if (uploadError) {
      setError(uploadError);
      return;
    }

    setUploadingPhoto(true);
    setError(null);
    try {
      const prepared = await prepareArtworkUploadFile(photo);
      const updated = await api.upload<Artwork>(
        `/api/artworks/${artwork.id}/image`,
        prepared.file,
        {
          captured_at: prepared.capturedAt ?? undefined,
        }
      );
      setArtwork(updated);
      setPhotoOpen(false);
      setPhoto(null);
      setPreviewUrl(null);
      setRegionOpen(true);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not upload photo.");
    } finally {
      setUploadingPhoto(false);
    }
  }

  async function uploadLabelPhoto() {
    if (!photo) return;

    const uploadError = validateArtworkUploadFile(photo);
    if (uploadError) {
      setError(uploadError);
      return;
    }

    setUploadingLabel(true);
    setError(null);
    try {
      const prepared = await prepareArtworkUploadFile(photo);
      const updated = await api.upload<Artwork>(
        `/api/artworks/${artwork.id}/label-image`,
        prepared.file
      );
      setArtwork(updated);
      setPhotoOpen(false);
      setPhoto(null);
      setPreviewUrl(null);
      setPhotoMode("artwork");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not upload label photo.");
    } finally {
      setUploadingLabel(false);
    }
  }

  function handleAnnotationAccepted(annotation: Annotation) {
    setAnnotations((current) => [...current, annotation]);
    router.refresh();
  }

  function placeAnnotationOnImage(annotationId: number) {
    setPendingAnnotationPlacement(artwork.id, annotationId);
    router.push(`/artworks/${artwork.id}/annotate`);
  }

  async function refetchAnnotations() {
    const refreshed = await api.get<Annotation[]>(
      `/api/artworks/${artwork.id}/annotations`
    );
    setAnnotations(refreshed);
    return refreshed;
  }

  function openAnnotationDetail(annotation: Annotation) {
    setSelectedAnnotation(annotation);
    setAnnotationSuccess(null);
    setError(null);
  }

  async function saveAnnotationDetail(values: AnnotationPinFormValues) {
    if (!selectedAnnotation || !values.text.trim()) return;
    setSavingAnnotation(true);
    setError(null);
    setAnnotationSuccess(null);
    try {
      await api.patch<Annotation>(
        `/api/artworks/${artwork.id}/annotations/${selectedAnnotation.id}`,
        formValuesToAnnotationPayload(values)
      );
      const refreshed = await refetchAnnotations();
      const updated = refreshed.find((item) => item.id === selectedAnnotation.id);
      if (updated) setSelectedAnnotation(updated);
      setAnnotationSuccess("Annotation saved.");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save annotation.");
    } finally {
      setSavingAnnotation(false);
    }
  }

  async function deleteAnnotation() {
    if (!deletingAnnotation) return;
    setDeleteAnnotationLoading(true);
    setError(null);
    try {
      await api.delete(
        `/api/artworks/${artwork.id}/annotations/${deletingAnnotation.id}`
      );
      await refetchAnnotations();
      setDeletingAnnotation(null);
      setSelectedAnnotation(null);
      setAnnotationSuccess("Annotation deleted.");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete annotation.");
    } finally {
      setDeleteAnnotationLoading(false);
    }
  }

  async function deleteArtwork() {
    setDeleteLoading(true);
    setError(null);
    try {
      await api.delete(`/api/artworks/${artwork.id}`);
      router.push(artwork.visit_id ? `/visits/${artwork.visit_id}` : "/visits");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete artwork.");
      setDeleteLoading(false);
    }
  }

  return (
  <ArtworkImageLookupPanel
    artwork={artwork}
    canEdit={canEdit}
    hasImage={hasImage}
    aiTitleHint={labelLookupHints?.title ?? researchHints?.lookupTitle ?? researchHints?.title}
    aiArtistHint={labelLookupHints?.artist ?? researchHints?.lookupArtist ?? researchHints?.artist}
    aiMediumHint={researchHints?.medium}
    onApplied={handleLookupApplied}
  >
  <>
    <div className="-mx-4 space-y-5 pb-28 sm:mx-0 sm:space-y-8 sm:pb-10">
      <ArtworkImageLookupDebug
        canEdit={canEdit}
        hasImage={hasImage}
        imageUrl={displayRaw}
        lookupMounted
      />

      <ArtworkImageDebug artwork={artwork} />

      <section className="overflow-hidden bg-[#f3efe8] sm:rounded-xl sm:border sm:border-border">
        {hasImage ? (
          <>
            <ArtworkImage
              artwork={artwork}
              imgClassName="max-h-[min(70dvh,640px)]"
              fallback={
                <div className="flex min-h-48 flex-col items-center justify-center gap-2 px-6 py-10 text-center text-sm text-muted-foreground">
                  <ArtworkImagePlaceholder />
                  <p>Image unavailable — you can still replace it with an official museum image.</p>
                </div>
              }
            />
            {!authLoading && canEdit ? (
              <div className="flex flex-col gap-2 border-t border-border/60 bg-background px-4 py-3">
                <ArtworkImageLookupAction variant="replace" fullWidth primary />
                <Button
                  type="button"
                  variant="outline"
                  size="touch"
                  className="w-full"
                  onClick={() => setRegionOpen(true)}
                >
                  {artworkHasImageRegion(artwork) ? "Adjust artwork area" : "Set artwork area"}
                </Button>
              </div>
            ) : null}
            {artworkHasImageRegion(artwork) ? (
              <p className="border-t border-border/60 bg-muted/30 px-4 py-2 text-center text-xs text-muted-foreground">
                Showing cropped artwork area · full photo preserved
              </p>
            ) : null}
          </>
        ) : (
          <div className="flex min-h-48 flex-col items-center justify-center gap-4 px-6 py-10 text-center text-sm text-muted-foreground">
            <Camera className="size-8 opacity-50" />
            <p>No photo yet. Capture your own, or find an official museum image.</p>
            {!authLoading && canEdit ? (
              <ArtworkImageLookupAction fullWidth primary className="max-w-sm" />
            ) : !authLoading ? (
              <SignInInlineHint hint="officialImage" />
            ) : null}
          </div>
        )}
      </section>

      {!canEdit && !authLoading ? (
        <div className="px-4 sm:px-0">
          <AuthGate />
        </div>
      ) : null}

      {canEdit ? (
        <div className="px-4 sm:px-0">
          <PhotoCaptureDateSuggestion
            artwork={artwork}
            onVisitUpdated={() => router.refresh()}
          />
        </div>
      ) : null}

      <section className="space-y-3 px-4 sm:px-0">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {[artwork.museum_gallery, artwork.medium].filter(Boolean).join(" · ")}
            </p>
            <h1 className="font-heading text-2xl font-normal leading-tight sm:text-3xl">
              {artworkDisplayTitle(artwork.title)}
            </h1>
            <p className="text-base text-muted-foreground">
              {[artwork.artist, artwork.year_period].filter(Boolean).join(" · ")}
            </p>
          </div>
          {canEdit ? (
            <AdminActionsMenu
              label="Artwork actions"
              onEdit={() => setEditOpen(true)}
              onDelete={() => setDeleteOpen(true)}
              extraActions={
                researchHints?.title || researchHints?.artist
                  ? [
                      {
                        label: "Apply suggested metadata",
                        onClick: () => {
                          researchRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                          openApplyReviewRef.current?.();
                        },
                      },
                    ]
                  : []
              }
            />
          ) : null}
        </div>
        {artwork.catalog_source ? (
          <p className="text-xs text-muted-foreground">
            Image via {artwork.catalog_source}
            {artwork.catalog_accession_number
              ? ` · ${artwork.catalog_accession_number}`
              : null}
            {artwork.catalog_object_url ? (
              <>
                {" · "}
                <a
                  href={artwork.catalog_object_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline-offset-2 hover:underline"
                >
                  Collection record
                </a>
              </>
            ) : null}
          </p>
        ) : null}
      </section>

      {canEdit ? (
        <div className="hidden flex-wrap gap-2 px-4 sm:px-0 md:flex">
          <Button size="touch" variant="outline" onClick={() => setNoteOpen(true)}>
            Add note
          </Button>
          <ButtonLink href={`/artworks/${artwork.id}/annotate`} variant="outline">
            Add annotation
          </ButtonLink>
          <Button size="touch" variant="outline" onClick={() => setPhotoOpen(true)}>
            Add photo
          </Button>
          <ArtworkImageLookupAction variant={hasImage ? "replace" : "find"} />
        </div>
      ) : null}

      <div ref={enrichmentRef} className="space-y-5 px-4 sm:px-0">
        <ArtworkLabelSection
          artwork={artwork}
          canEdit={canEdit}
          onArtworkUpdated={handleArtworkUpdated}
        />
        <ArtworkEnrichmentPanel
          artwork={artwork}
          canEdit={canEdit}
          hasImage={hasImage}
          autoFocus={autoEnrich}
          culturalEntities={culturalEntities}
          onArtworkUpdated={handleArtworkUpdated}
          onAnnotationAccepted={handleAnnotationAccepted}
          onHintsChange={setResearchHints}
          onApplyReviewReady={(openReview) => {
            openApplyReviewRef.current = openReview;
          }}
        />
      </div>

      <section className="px-4 sm:px-0">
        {canEdit ? (
          <button
            type="button"
            onClick={() => setNoteOpen(true)}
            className="w-full rounded-xl border border-border bg-card p-4 text-left transition-colors active:bg-muted/50"
          >
            <p className="mb-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">
              Personal note
            </p>
            <p className="text-base leading-relaxed">
              {artwork.personal_notes?.trim()
                ? artwork.personal_notes
                : "Tap to jot a quick note while you're in the gallery."}
            </p>
          </button>
        ) : (
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="mb-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">
              Personal note
            </p>
            <p className="text-base leading-relaxed">
              {artwork.personal_notes?.trim() || "No note recorded yet."}
            </p>
          </div>
        )}
      </section>

      <section className="space-y-3 px-4 sm:px-0">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-xl">Annotations</h2>
          <span className="text-sm text-muted-foreground">
            {placedAnnotations.length} placed
            {unplacedAnnotations.length > 0
              ? ` · ${unplacedAnnotations.length} to place`
              : ""}
          </span>
        </div>

        {annotations.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
            {canEdit ? (
              "Tap Annotate below to mark details on the image."
            ) : (
              <>
                <p>No annotations yet.</p>
                {!authLoading ? (
                  <SignInInlineHint hint="annotate" className="mt-2" />
                ) : null}
              </>
            )}
          </div>
        ) : (
          <AnnotationOverviewList
            placed={placedAnnotations}
            unplaced={unplacedAnnotations}
            canEdit={canEdit}
            culturalEntities={culturalEntities}
            onOpenDetail={openAnnotationDetail}
            onDelete={setDeletingAnnotation}
            onPlaceOnImage={placeAnnotationOnImage}
            showPlaceOnImage={Boolean(canEdit && resolvedDisplayUrl)}
          />
        )}
      </section>

      <div ref={researchRef} className="px-4 sm:px-0">
        <ResearchPanel
          artwork={artwork}
          canEdit={canEdit}
          hasImage={hasImage}
          culturalEntities={culturalEntities}
          historyOnly
          onReady={(generate) => {
            generateResearchRef.current = generate;
          }}
          onAnnotationAccepted={handleAnnotationAccepted}
          onArtworkUpdated={handleArtworkUpdated}
          onHintsChange={setResearchHints}
          onApplyReviewReady={(openReview) => {
            openApplyReviewRef.current = openReview;
          }}
        />
      </div>
    </div>

    {canEdit ? (
      <div
        className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        <div className="mx-auto grid max-w-lg grid-cols-5 gap-1 px-2 py-2">
          <ActionButton icon={Pencil} label="Note" onClick={() => setNoteOpen(true)} />
          <ActionButton
            icon={MapPin}
            label="Annotate"
            href={`/artworks/${artwork.id}/annotate`}
          />
          <ActionButton icon={Camera} label="Photo" onClick={() => setPhotoOpen(true)} />
          <LookupActionButton hasImage={hasImage} label={hasImage ? "Replace" : "Find"} />
          <ActionButton icon={Sparkles} label="AI" onClick={scrollToEnrichment} />
        </div>
      </div>
    ) : null}

    {canEdit ? (
      <>
        <BottomSheet
      open={noteOpen}
      onOpenChange={setNoteOpen}
      title="Personal note"
      description="Quick thoughts while you're in front of the work."
    >
      <div className="space-y-4 pb-2">
        <Textarea
          rows={5}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Color, mood, what surprised you…"
        />
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button size="touch" className="w-full" disabled={savingNote} onClick={saveNote}>
          {savingNote ? "Saving…" : "Save note"}
        </Button>
      </div>
    </BottomSheet>

    <BottomSheet
      open={photoOpen}
      onOpenChange={(open) => {
        setPhotoOpen(open);
        if (!open) {
          setPhotoMode("artwork");
          setPhoto(null);
          setPreviewUrl(null);
          setError(null);
        }
      }}
      title="Add photo"
      description="Capture the artwork or the museum wall label."
    >
      <div className="space-y-4 pb-2">
        <div className="grid grid-cols-2 gap-2">
          <Button
            type="button"
            variant={photoMode === "artwork" ? "default" : "outline"}
            size="sm"
            className="min-h-10"
            onClick={() => setPhotoMode("artwork")}
          >
            Artwork photo
          </Button>
          <Button
            type="button"
            variant={photoMode === "label" ? "default" : "outline"}
            size="sm"
            className="min-h-10"
            onClick={() => setPhotoMode("label")}
          >
            Label photo
          </Button>
        </div>
        <CameraUpload
          previewUrl={photoMode === "artwork" ? previewUrl ?? resolvedDisplayUrl : previewUrl}
          selectedFile={photo}
          disabled={uploadingPhoto || uploadingLabel}
          error={error}
          onSelect={(file) => {
            const validationError = validateArtworkUploadFile(file);
            if (validationError) {
              setError(validationError);
              setPhoto(null);
              setPreviewUrl(null);
              return;
            }
            setError(null);
            setPhoto(file);
            setPreviewUrl(URL.createObjectURL(file));
          }}
        />
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button
          size="touch"
          className="w-full"
          disabled={(uploadingPhoto || uploadingLabel || !photo)}
          onClick={() => void (photoMode === "label" ? uploadLabelPhoto() : uploadPhoto())}
        >
          {uploadingPhoto || uploadingLabel
            ? "Uploading…"
            : photoMode === "label"
              ? "Upload label photo"
              : "Upload artwork photo"}
        </Button>
      </div>
    </BottomSheet>

    <BottomSheet
      open={editOpen}
      onOpenChange={setEditOpen}
      title="Edit artwork"
      description="Update title, artist, and other metadata."
    >
      <ProgressiveArtworkForm
        artwork={artwork}
        visitId={artwork.visit_id ?? undefined}
        compact
        redirectOnSave={false}
        onComplete={(updated) => {
          if (updated) setArtwork(updated);
          setEditOpen(false);
          router.refresh();
        }}
      />
    </BottomSheet>

      </>
    ) : null}

    <AnnotationDetailSheet
      annotation={selectedAnnotation}
      open={selectedAnnotation !== null}
      onOpenChange={(open) => {
        if (!open) {
          setSelectedAnnotation(null);
          setAnnotationSuccess(null);
          setError(null);
        }
      }}
      canEdit={canEdit}
      culturalEntities={culturalEntities}
      tagSuggestions={tagSuggestions}
      saving={savingAnnotation}
      error={error}
      success={annotationSuccess}
      onSave={saveAnnotationDetail}
      onDelete={() => {
        if (selectedAnnotation) setDeletingAnnotation(selectedAnnotation);
      }}
      onMovePin={
        selectedAnnotation &&
        selectedAnnotation.x_percent != null &&
        selectedAnnotation.y_percent != null
          ? () => {
              placeAnnotationOnImage(selectedAnnotation.id);
              setSelectedAnnotation(null);
            }
          : undefined
      }
      onPlaceOnImage={
        selectedAnnotation?.x_percent == null
          ? () => {
              if (selectedAnnotation) {
                placeAnnotationOnImage(selectedAnnotation.id);
                setSelectedAnnotation(null);
              }
            }
          : undefined
      }
    />

    {canEdit && hasImage ? (
      <ArtworkRegionSheet
        open={regionOpen}
        onOpenChange={setRegionOpen}
        artwork={artwork}
        onSaved={handleRegionSaved}
      />
    ) : null}

    <ConfirmDeleteDialog
      open={deleteOpen}
      onOpenChange={setDeleteOpen}
      title="Delete artwork?"
      description="This permanently removes the artwork, its annotations, research notes, and uploaded images from disk when possible."
      loading={deleteLoading}
      onConfirm={deleteArtwork}
    />

    <ConfirmDeleteDialog
      open={deletingAnnotation !== null}
      onOpenChange={(open) => {
        if (!open) setDeletingAnnotation(null);
      }}
      title="Delete annotation?"
      description="This pin and its note will be removed permanently."
      loading={deleteAnnotationLoading}
      onConfirm={deleteAnnotation}
    />
  </>
  </ArtworkImageLookupPanel>
  );
}

function LookupActionButton({ hasImage, label }: { hasImage: boolean; label: string }) {
  const { openLookup, canEdit } = useArtworkImageLookup();

  if (!canEdit) return null;

  return (
    <button
      type="button"
      onClick={() => openLookup()}
      data-testid="artwork-official-image-lookup-mobile"
      className="flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1.5 text-[11px] text-foreground transition-colors active:bg-muted"
      aria-label={hasImage ? "Replace official image" : "Find official image"}
    >
      <ImageIcon className="size-5" strokeWidth={1.75} />
      <span>{label}</span>
    </button>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  href,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
  onClick?: () => void;
  href?: string;
}) {
  const className =
    "flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1.5 text-[11px] text-foreground transition-colors active:bg-muted";

  if (href) {
    return (
      <Link href={href} className={className} aria-label={label}>
        <Icon className="size-5" strokeWidth={1.75} />
        <span>{label}</span>
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className} aria-label={label}>
      <Icon className="size-5" strokeWidth={1.75} />
      <span>{label}</span>
    </button>
  );
}
