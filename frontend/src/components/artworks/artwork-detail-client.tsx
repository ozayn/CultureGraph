"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Camera, ImageIcon, MapPin, Pencil, Sparkles } from "lucide-react";
import { useRef, useState, useMemo } from "react";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { AnnotationPinForm } from "@/components/annotations/annotation-pin-form";
import { AnnotationPinMeta } from "@/components/annotations/annotation-pin-meta";
import {
  ArtworkImageLookupAction,
  ArtworkImageLookupDebug,
  ArtworkImageLookupPanel,
  useArtworkImageLookup,
} from "@/components/artworks/artwork-image-lookup-panel";
import { AuthGate } from "@/components/auth/auth-gate";
import { SignInInlineHint } from "@/components/auth/sign-in-inline-hint";
import { ArtworkRegionSheet } from "@/components/artworks/artwork-region-sheet";
import { ArtworkImage, ArtworkImagePlaceholder } from "@/components/artworks/artwork-image";
import { PhotoCaptureDateSuggestion } from "@/components/artworks/photo-capture-date-suggestion";
import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";
import { ResearchPanel } from "@/components/artworks/research-panel";
import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ButtonLink } from "@/components/ui/button-link";
import { Button } from "@/components/ui/button";
import { CameraUpload } from "@/components/ui/camera-upload";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { displayImageUrl } from "@/lib/media-url";
import { artworkDisplayTitle } from "@/lib/artwork-metadata";
import { artworkHasImageRegion } from "@/lib/artwork-region";
import { useAuth } from "@/contexts/auth-context";
import {
  annotationToFormValues,
  emptyAnnotationPinFormValues,
  formValuesToAnnotationPayload,
  type AnnotationPinFormValues,
} from "@/lib/annotation-form";
import { buildAnnotationTagSuggestions } from "@/lib/annotation-suggestions";
import type { ResearchMetadataHints } from "@/lib/artwork-metadata";
import { splitAnnotationsByPlacement } from "@/lib/annotation-placement";
import { setPendingAnnotationPlacement } from "@/lib/pending-annotation-placement";
import { validateArtworkUploadFile } from "@/lib/upload-validation";
import {
  CATEGORY_LABELS,
  type Annotation,
  type Artwork,
  type CulturalEntity,
} from "@/lib/types";

interface ArtworkDetailClientProps {
  artwork: Artwork;
  annotations: Annotation[];
  culturalEntities?: CulturalEntity[];
}

export function ArtworkDetailClient({
  artwork: initialArtwork,
  annotations: initialAnnotations,
  culturalEntities = [],
}: ArtworkDetailClientProps) {
  const router = useRouter();
  const { canEdit, loading: authLoading } = useAuth();
  const researchRef = useRef<HTMLDivElement>(null);
  const generateResearchRef = useRef<(() => Promise<void>) | null>(null);
  const [artwork, setArtwork] = useState(initialArtwork);
  const [annotations, setAnnotations] = useState(initialAnnotations);
  const [noteOpen, setNoteOpen] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [regionOpen, setRegionOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [editingAnnotation, setEditingAnnotation] = useState<Annotation | null>(null);
  const [deletingAnnotation, setDeletingAnnotation] = useState<Annotation | null>(null);
  const [deleteAnnotationLoading, setDeleteAnnotationLoading] = useState(false);
  const [annotationFormValues, setAnnotationFormValues] = useState<AnnotationPinFormValues>(
    emptyAnnotationPinFormValues()
  );
  const [savingAnnotation, setSavingAnnotation] = useState(false);

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
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resolvedDisplayUrl = useMemo(
    () => displayImageUrl(artwork.image_url),
    [artwork.image_url]
  );
  const hasImage = Boolean(artwork.image_url);

  const openApplyReviewRef = useRef<(() => void) | null>(null);
  const [researchHints, setResearchHints] = useState<ResearchMetadataHints | null>(null);

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
      const updated = await api.upload<Artwork>(
        `/api/artworks/${artwork.id}/image`,
        photo
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

  function triggerResearch() {
    void generateResearchRef.current?.();
    researchRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleAnnotationAccepted(annotation: Annotation) {
    setAnnotations((current) => [...current, annotation]);
    router.refresh();
  }

  function placeAnnotationOnImage(annotationId: number) {
    setPendingAnnotationPlacement(artwork.id, annotationId);
    router.push(`/artworks/${artwork.id}/annotate`);
  }

  function openAnnotationEditor(annotation: Annotation) {
    setEditingAnnotation(annotation);
    setAnnotationFormValues(annotationToFormValues(annotation));
    setError(null);
  }

  async function saveAnnotationEdit() {
    if (!editingAnnotation || !annotationFormValues.text.trim()) return;
    setSavingAnnotation(true);
    setError(null);
    try {
      const updated = await api.patch<Annotation>(
        `/api/artworks/${artwork.id}/annotations/${editingAnnotation.id}`,
        formValuesToAnnotationPayload(annotationFormValues)
      );
      setAnnotations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
      setEditingAnnotation(null);
      setAnnotationFormValues(emptyAnnotationPinFormValues());
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
      setAnnotations((current) =>
        current.filter((item) => item.id !== deletingAnnotation.id)
      );
      setDeletingAnnotation(null);
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
    aiTitleHint={researchHints?.title}
    aiArtistHint={researchHints?.artist}
    aiMediumHint={researchHints?.medium}
    onApplied={handleLookupApplied}
  >
  <>
    <div className="-mx-4 space-y-5 pb-28 sm:mx-0 sm:space-y-8 sm:pb-10">
      <ArtworkImageLookupDebug
        canEdit={canEdit}
        hasImage={hasImage}
        imageUrl={artwork.image_url}
        lookupMounted
      />

      <section className="overflow-hidden bg-[#f3efe8] sm:rounded-xl sm:border sm:border-border">
        {hasImage ? (
          <>
            <ArtworkImage
              imageUrl={artwork.image_url}
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
                researchHints
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
          <Button size="touch" variant="outline" onClick={triggerResearch}>
            Research with AI
          </Button>
        </div>
      ) : null}

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
          <div className="space-y-4">
            {unplacedAnnotations.length > 0 ? (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-muted-foreground">
                  Annotations to place
                </h3>
                <ul className="space-y-3">
                  {unplacedAnnotations.map((annotation) => (
                    <li
                      key={annotation.id}
                      className="rounded-xl border border-dashed border-border bg-muted/20 p-4"
                    >
                      <div className="mb-2 flex items-start justify-between gap-2">
                        <Badge variant="secondary">
                          {CATEGORY_LABELS[annotation.category]}
                        </Badge>
                        {canEdit ? (
                          <AdminActionsMenu
                            label={`Actions for unplaced annotation ${annotation.id}`}
                            onEdit={() => openAnnotationEditor(annotation)}
                            onDelete={() => setDeletingAnnotation(annotation)}
                          />
                        ) : null}
                      </div>
                      <p className="text-base leading-relaxed">{annotation.text}</p>
                      <AnnotationPinMeta
                        annotation={annotation}
                        culturalEntities={culturalEntities}
                      />
                      {canEdit && resolvedDisplayUrl ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="mt-3 min-h-10"
                          onClick={() => placeAnnotationOnImage(annotation.id)}
                        >
                          Place on image
                        </Button>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {placedAnnotations.length > 0 ? (
              <ul className="space-y-3">
                {placedAnnotations.map((annotation, index) => (
                  <li
                    key={annotation.id}
                    className="rounded-xl border border-border bg-card p-4"
                  >
                    <div className="mb-2 flex items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex size-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                          {index + 1}
                        </span>
                        <Badge variant="secondary">
                          {CATEGORY_LABELS[annotation.category]}
                        </Badge>
                      </div>
                      {canEdit ? (
                        <AdminActionsMenu
                          label={`Actions for annotation ${index + 1}`}
                          onEdit={() => openAnnotationEditor(annotation)}
                          onDelete={() => setDeletingAnnotation(annotation)}
                        />
                      ) : null}
                    </div>
                    <p className="text-base leading-relaxed">{annotation.text}</p>
                    <AnnotationPinMeta
                      annotation={annotation}
                      culturalEntities={culturalEntities}
                    />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        )}
      </section>

      <div ref={researchRef} className="px-4 sm:px-0">
        <ResearchPanel
          artwork={artwork}
          canEdit={canEdit}
          hasImage={hasImage}
          culturalEntities={culturalEntities}
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
          <ActionButton icon={Sparkles} label="AI" onClick={triggerResearch} />
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
      onOpenChange={setPhotoOpen}
      title="Add photo"
      description="Capture the artwork or wall label with your camera."
    >
      <div className="space-y-4 pb-2">
        <CameraUpload
          previewUrl={previewUrl ?? resolvedDisplayUrl}
          selectedFile={photo}
          disabled={uploadingPhoto}
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
          disabled={uploadingPhoto || !photo}
          onClick={uploadPhoto}
        >
          {uploadingPhoto ? "Uploading…" : "Upload photo"}
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

    <BottomSheet
      open={editingAnnotation !== null}
      onOpenChange={(open) => {
        if (!open) setEditingAnnotation(null);
      }}
      title="Edit annotation"
      description="Update category, note, tags, or links."
    >
      <AnnotationPinForm
        values={annotationFormValues}
        onChange={setAnnotationFormValues}
        culturalEntities={culturalEntities}
        tagSuggestions={tagSuggestions}
        noteId="edit-annotation-note"
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button
        size="touch"
        className="mt-4 w-full"
        disabled={savingAnnotation || !annotationFormValues.text.trim()}
        onClick={() => void saveAnnotationEdit()}
      >
        {savingAnnotation ? "Saving…" : "Save changes"}
      </Button>
    </BottomSheet>
      </>
    ) : null}

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
      onClick={openLookup}
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
