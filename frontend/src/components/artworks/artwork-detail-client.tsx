"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Camera, MapPin, Pencil, Sparkles } from "lucide-react";
import { useRef, useState } from "react";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { ArtworkImageLookupPanel } from "@/components/artworks/artwork-image-lookup-panel";
import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";
import { ResearchPanel } from "@/components/artworks/research-panel";
import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { ButtonLink } from "@/components/ui/button-link";
import { Button } from "@/components/ui/button";
import { CameraUpload } from "@/components/ui/camera-upload";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, mediaUrl } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { validateArtworkUploadFile } from "@/lib/upload-validation";
import {
  ANNOTATION_CATEGORIES,
  CATEGORY_LABELS,
  type Annotation,
  type AnnotationCategory,
  type Artwork,
} from "@/lib/types";
import { cn } from "@/lib/utils";

interface ArtworkDetailClientProps {
  artwork: Artwork;
  annotations: Annotation[];
  imageSrc: string | null;
  museumName: string | null;
}

export function ArtworkDetailClient({
  artwork: initialArtwork,
  annotations: initialAnnotations,
  imageSrc: initialImageSrc,
  museumName,
}: ArtworkDetailClientProps) {
  const router = useRouter();
  const { canEdit } = useAuth();
  const researchRef = useRef<HTMLDivElement>(null);
  const generateResearchRef = useRef<(() => Promise<void>) | null>(null);
  const [artwork, setArtwork] = useState(initialArtwork);
  const [annotations, setAnnotations] = useState(initialAnnotations);
  const [imageSrc, setImageSrc] = useState(initialImageSrc);
  const [noteOpen, setNoteOpen] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [editingAnnotation, setEditingAnnotation] = useState<Annotation | null>(null);
  const [deletingAnnotation, setDeletingAnnotation] = useState<Annotation | null>(null);
  const [deleteAnnotationLoading, setDeleteAnnotationLoading] = useState(false);
  const [annotationCategory, setAnnotationCategory] = useState<AnnotationCategory>("observation");
  const [annotationText, setAnnotationText] = useState("");
  const [savingAnnotation, setSavingAnnotation] = useState(false);
  const [note, setNote] = useState(artwork.personal_notes ?? "");
  const [savingNote, setSavingNote] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      setImageSrc(mediaUrl(updated.image_url));
      setPhotoOpen(false);
      setPhoto(null);
      setPreviewUrl(null);
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

  function openAnnotationEditor(annotation: Annotation) {
    setEditingAnnotation(annotation);
    setAnnotationCategory(annotation.category);
    setAnnotationText(annotation.text);
    setError(null);
  }

  async function saveAnnotationEdit() {
    if (!editingAnnotation || !annotationText.trim()) return;
    setSavingAnnotation(true);
    setError(null);
    try {
      const updated = await api.patch<Annotation>(
        `/api/artworks/${artwork.id}/annotations/${editingAnnotation.id}`,
        {
          category: annotationCategory,
          text: annotationText.trim(),
        }
      );
      setAnnotations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
      setEditingAnnotation(null);
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
  <>
    <div className="-mx-4 space-y-5 pb-28 sm:mx-0 sm:space-y-8 sm:pb-10">
      <section className="overflow-hidden bg-[#f3efe8] sm:rounded-xl sm:border sm:border-border">
        {imageSrc ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageSrc}
            alt={artwork.title}
            className="block w-full object-contain"
            style={{ maxHeight: "min(70dvh, 640px)" }}
          />
        ) : (
          <div className="flex min-h-48 flex-col items-center justify-center gap-3 px-6 py-10 text-center text-sm text-muted-foreground">
            <Camera className="size-8 opacity-50" />
            <p>No photo yet. Tap Photo below to capture the label or artwork.</p>
          </div>
        )}
      </section>

      {!imageSrc && canEdit ? (
        <ArtworkImageLookupPanel
          artwork={artwork}
          museumName={museumName}
          canEdit={canEdit}
          onApplied={(updated) => {
            setArtwork(updated);
            setImageSrc(mediaUrl(updated.image_url));
            router.refresh();
          }}
        />
      ) : null}

      <section className="space-y-3 px-4 sm:px-0">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {[artwork.museum_gallery, artwork.medium].filter(Boolean).join(" · ")}
            </p>
            <h1 className="font-heading text-2xl font-normal leading-tight sm:text-3xl">
              {artwork.title}
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
          <span className="text-sm text-muted-foreground">{annotations.length} pins</span>
        </div>

        {annotations.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
            Tap Annotate below to mark details on the image.
          </div>
        ) : (
          <ul className="space-y-3">
            {annotations.map((annotation, index) => (
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
              </li>
            ))}
          </ul>
        )}
      </section>

      {!canEdit ? (
        <div className="px-4 sm:px-0">
          <SignInPrompt compact />
        </div>
      ) : null}

      <div ref={researchRef} className="px-4 sm:px-0">
        <ResearchPanel
          artworkId={artwork.id}
          canEdit={canEdit}
          onReady={(generate) => {
            generateResearchRef.current = generate;
          }}
        />
      </div>
    </div>

    {canEdit ? (
      <div
        className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        <div className="mx-auto grid max-w-lg grid-cols-4 gap-1 px-2 py-2">
          <ActionButton icon={Pencil} label="Note" onClick={() => setNoteOpen(true)} />
          <ActionButton
            icon={MapPin}
            label="Annotate"
            href={`/artworks/${artwork.id}/annotate`}
          />
          <ActionButton icon={Camera} label="Photo" onClick={() => setPhotoOpen(true)} />
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
          previewUrl={previewUrl ?? imageSrc}
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
      description="Update category or note text."
    >
      <div className="space-y-4 pb-2">
        <div className="space-y-2">
          <Label>Category</Label>
          <div className="flex flex-wrap gap-2">
            {ANNOTATION_CATEGORIES.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setAnnotationCategory(item)}
                className={cn(
                  "min-h-11 rounded-full border px-4 py-2 text-sm transition-colors",
                  annotationCategory === item
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground active:bg-muted"
                )}
              >
                {CATEGORY_LABELS[item]}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-annotation-note">Note</Label>
          <Textarea
            id="edit-annotation-note"
            rows={4}
            value={annotationText}
            onChange={(event) => setAnnotationText(event.target.value)}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button
          size="touch"
          className="w-full"
          disabled={savingAnnotation || !annotationText.trim()}
          onClick={() => void saveAnnotationEdit()}
        >
          {savingAnnotation ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </BottomSheet>
      </>
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
      <Link href={href} className={className}>
        <Icon className="size-5" strokeWidth={1.75} />
        <span>{label}</span>
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      <Icon className="size-5" strokeWidth={1.75} />
      <span>{label}</span>
    </button>
  );
}
