"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CameraUpload } from "@/components/ui/camera-upload";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { Artwork } from "@/lib/types";

interface ProgressiveArtworkFormProps {
  visitId?: number;
  artwork?: Artwork;
  onComplete?: () => void;
  compact?: boolean;
}

export function ProgressiveArtworkForm({
  visitId,
  artwork,
  onComplete,
  compact,
}: ProgressiveArtworkFormProps) {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState(artwork?.title ?? "");
  const [artist, setArtist] = useState(artwork?.artist ?? "");
  const [yearPeriod, setYearPeriod] = useState(artwork?.year_period ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const previewUrl = useMemo(
    () => (photo ? URL.createObjectURL(photo) : null),
    [photo]
  );

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function saveArtwork(includeDetails: boolean) {
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      title: title.trim(),
      artist: includeDetails && artist.trim() ? artist.trim() : null,
      year_period: includeDetails && yearPeriod.trim() ? yearPeriod.trim() : null,
      medium: artwork?.medium ?? null,
      museum_gallery: artwork?.museum_gallery ?? null,
      personal_notes: artwork?.personal_notes ?? null,
      visit_id: visitId ?? artwork?.visit_id ?? null,
    };

    try {
      const saved = artwork
        ? await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload)
        : await api.post<Artwork>("/api/artworks", payload);

      if (photo) {
        await api.upload<Artwork>(`/api/artworks/${saved.id}/image`, photo);
      }

      onComplete?.();
      router.push(`/artworks/${saved.id}`);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save artwork.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={compact ? "space-y-4" : "space-y-5"}>
      <p className="text-sm text-muted-foreground">
        Step {step} of 2 · {step === 1 ? "Essentials" : "Optional details"}
      </p>

      {step === 1 ? (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="artwork-title">Title</Label>
            <Input
              id="artwork-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="What are you looking at?"
              autoFocus
            />
          </div>

          <CameraUpload
            previewUrl={previewUrl}
            disabled={loading}
            onSelect={setPhoto}
          />
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
        </div>
      )}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

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
              disabled={loading || !title.trim()}
              onClick={() => setStep(2)}
            >
              Add details
            </Button>
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="sm:flex-1"
              disabled={loading || !title.trim()}
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
