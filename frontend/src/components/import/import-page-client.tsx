"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { MuseumAutocomplete } from "@/components/museums/museum-autocomplete";
import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import {
  CATEGORY_LABELS,
  type ArtworkImportDraft,
  type MuseumNotesImportResponse,
  type Visit,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const SAMPLE_NOTES = `Smithsonian American Art Museum visit notes

Grandma Moses — nighttime baseball scene, small-town lights, folk warmth
Thomas Moran and Manifest Destiny — dramatic western landscape, expansion myth
Sanford Biggers, Reclining Liberty near Brooklyn Waterfront references
Alexis Rockman, Manifest Destiny — flooded future city, ecological dread
Sam Gilliam — draped canvas, color fields spilling off the wall
Leonardo Drew — found objects, weathered wood and rust`;

type ImportStep = "paste" | "review";

interface ReviewArtwork extends ArtworkImportDraft {
  selected: boolean;
  saveAnnotations: boolean;
}

function buildPersonalNotes(artwork: ReviewArtwork): string | null {
  const parts: string[] = [];
  if (artwork.notes?.trim()) parts.push(artwork.notes.trim());
  if (artwork.themes.length) {
    parts.push(`Themes: ${artwork.themes.join(", ")}`);
  }
  if (artwork.concepts.length) {
    parts.push(`Concepts: ${artwork.concepts.join(", ")}`);
  }
  return parts.length ? parts.join("\n\n") : null;
}

function formatConceptLinks(links: MuseumNotesImportResponse["concept_links"]): string {
  return links
    .map((link) => `${link.source} → ${link.target} (${link.relationship})`)
    .join("\n");
}

export function ImportPageClient() {
  const router = useRouter();
  const { canEdit } = useAuth();
  const [step, setStep] = useState<ImportStep>("paste");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [notesText, setNotesText] = useState("");
  const [museumName, setMuseumName] = useState("Smithsonian American Art Museum");
  const [city, setCity] = useState("Washington, DC");
  const [visitDate, setVisitDate] = useState(new Date().toISOString().slice(0, 10));

  const [saveVisit, setSaveVisit] = useState(true);
  const [visitSummary, setVisitSummary] = useState("");
  const [conceptLinks, setConceptLinks] = useState<MuseumNotesImportResponse["concept_links"]>(
    []
  );
  const [artworks, setArtworks] = useState<ReviewArtwork[]>([]);
  const [source, setSource] = useState<string>("mock");

  async function extractEntries() {
    if (!canEdit) {
      setError("Sign in to edit CultureGraph.");
      return;
    }
    if (!notesText.trim()) {
      setError("Paste your museum notes first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await api.post<MuseumNotesImportResponse>("/api/import/museum-notes", {
        text: notesText.trim(),
        default_museum: museumName.trim() || "Smithsonian American Art Museum",
        default_city: city.trim() || "Washington, DC",
        visit_date: visitDate || null,
      });

      setVisitSummary(result.visit.summary);
      setConceptLinks(result.concept_links);
      setSource(result.source);
      setArtworks(
        result.artworks.map((artwork) => ({
          ...artwork,
          selected: true,
          saveAnnotations: true,
        }))
      );
      setMuseumName(result.visit.museum_name);
      setCity(result.visit.city);
      setVisitDate(result.visit.visit_date);
      setStep("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not extract entries.");
    } finally {
      setLoading(false);
    }
  }

  function updateArtwork(index: number, patch: Partial<ReviewArtwork>) {
    setArtworks((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item))
    );
  }

  async function saveSelected() {
    if (!canEdit) {
      setError("Sign in to edit CultureGraph.");
      return;
    }
    const selectedArtworks = artworks.filter((artwork) => artwork.selected);
    if (!saveVisit && selectedArtworks.length === 0) {
      setError("Select a visit and/or at least one artwork to save.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      let visitId: number | null = null;

      if (saveVisit) {
        const conceptSection =
          conceptLinks.length > 0
            ? `\n\nConcept links:\n${formatConceptLinks(conceptLinks)}`
            : "";
        const visitNotes = [visitSummary.trim(), conceptSection.trim()]
          .filter(Boolean)
          .join("\n\n");

        const visit = await api.post<Visit>("/api/visits", {
          museum_name: museumName.trim(),
          city: city.trim(),
          visit_date: visitDate,
          notes: visitNotes || null,
        });
        visitId = visit.id;
      }

      for (const artwork of selectedArtworks) {
        const saved = await api.post<{ id: number }>("/api/artworks", {
          title: artwork.title?.trim() || "Untitled artwork",
          artist: artwork.artist?.trim() || null,
          year_period: artwork.period_or_year?.trim() || null,
          medium: artwork.medium?.trim() || null,
          personal_notes: buildPersonalNotes(artwork),
          visit_id: visitId,
        });

        if (artwork.saveAnnotations) {
          for (const annotation of artwork.suggested_annotations) {
            await api.post(`/api/artworks/${saved.id}/annotations`, {
              x_percent: 50,
              y_percent: 50,
              category: annotation.category,
              text: annotation.note,
            });
          }
        }
      }

      if (visitId) {
        router.push(`/visits/${visitId}`);
      } else if (selectedArtworks.length === 1) {
        router.push("/visits");
      } else {
        router.push("/visits");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save entries.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 pb-24 sm:space-y-8 sm:pb-8">
      <section className="space-y-2">
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground sm:text-sm">
          Import notes
        </p>
        <h2 className="font-heading text-2xl font-normal leading-tight sm:text-3xl">
          Turn messy museum notes into your notebook
        </h2>
        <p className="max-w-xl text-base leading-relaxed text-muted-foreground">
          Paste a tour outline, gallery walk, or ChatGPT summary. CultureGraph will draft visits,
          artworks, observations, concepts, and links for you to review before saving.
        </p>
      </section>

      {!canEdit ? <SignInPrompt /> : null}

      {step === "paste" ? (
        <section className="space-y-5 rounded-xl border border-border bg-card p-4 sm:p-5">
          <p className="text-sm text-muted-foreground">Step 1 of 2 · Paste notes</p>

          <div className="space-y-2">
            <Label htmlFor="import_notes">Museum notes</Label>
            <Textarea
              id="import_notes"
              rows={10}
              value={notesText}
              onChange={(event) => setNotesText(event.target.value)}
              placeholder="Paste rough notes from your visit or a museum tour outline…"
              className="min-h-[220px] text-base leading-relaxed"
            />
            <button
              type="button"
              className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              onClick={() => setNotesText(SAMPLE_NOTES)}
            >
              Load sample notes
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <MuseumAutocomplete
              id="import_museum"
              label="Default museum"
              value={museumName}
              onValueChange={setMuseumName}
              onMuseumSelect={(museum) => setCity(museum.city)}
              placeholder="Smithsonian American Art Museum"
            />
            <div className="space-y-2">
              <Label htmlFor="import_city">City</Label>
              <Input
                id="import_city"
                value={city}
                onChange={(event) => setCity(event.target.value)}
              />
            </div>
            <div className="space-y-2 sm:col-span-2 sm:max-w-xs">
              <Label htmlFor="import_date">Visit date</Label>
              <Input
                id="import_date"
                type="date"
                value={visitDate}
                onChange={(event) => setVisitDate(event.target.value)}
              />
            </div>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <Button
            type="button"
            size="touch"
            className="w-full sm:w-auto"
            disabled={loading || !canEdit}
            onClick={() => void extractEntries()}
          >
            {loading ? "Extracting…" : "Extract entries"}
          </Button>
        </section>
      ) : (
        <section className="space-y-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-foreground">
              Step 2 of 2 · Review draft ·{" "}
              <span className="text-foreground">{source === "claude" ? "Claude" : "Mock parser"}</span>
            </p>
            <Button type="button" variant="outline" size="touch" onClick={() => setStep("paste")}>
              Edit notes
            </Button>
          </div>

          <article className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 size-4 shrink-0 accent-foreground"
                checked={saveVisit}
                onChange={(event) => setSaveVisit(event.target.checked)}
              />
              <span className="space-y-1">
                <span className="block font-heading text-lg">Visit</span>
                <span className="block text-sm text-muted-foreground">
                  Save as a visit record with summary and concept links
                </span>
              </span>
            </label>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="review_museum">Museum</Label>
                <Input
                  id="review_museum"
                  value={museumName}
                  onChange={(event) => setMuseumName(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="review_city">City</Label>
                <Input
                  id="review_city"
                  value={city}
                  onChange={(event) => setCity(event.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="review_summary">Visit summary</Label>
              <Textarea
                id="review_summary"
                rows={3}
                value={visitSummary}
                onChange={(event) => setVisitSummary(event.target.value)}
              />
            </div>

            {conceptLinks.length > 0 ? (
              <div className="space-y-2">
                <p className="text-sm font-medium">Concept links</p>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {conceptLinks.map((link) => (
                    <li
                      key={`${link.source}-${link.target}`}
                      className="rounded-lg bg-muted/50 px-3 py-2"
                    >
                      <span className="text-foreground">{link.source}</span>
                      {" → "}
                      <span className="text-foreground">{link.target}</span>
                      <span className="text-muted-foreground"> · {link.relationship}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </article>

          <div className="space-y-4">
            <h3 className="font-heading text-xl">Artworks</h3>
            {artworks.map((artwork, index) => (
              <article
                key={`${artwork.artist ?? "unknown"}-${index}`}
                className={cn(
                  "space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5",
                  !artwork.selected && "opacity-60"
                )}
              >
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1 size-4 shrink-0 accent-foreground"
                    checked={artwork.selected}
                    onChange={(event) =>
                      updateArtwork(index, { selected: event.target.checked })
                    }
                  />
                  <span className="font-heading text-lg">
                    {artwork.title?.trim() || artwork.artist?.trim() || `Entry ${index + 1}`}
                  </span>
                </label>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Title</Label>
                    <Input
                      value={artwork.title ?? ""}
                      placeholder="Unknown — edit or leave blank"
                      onChange={(event) =>
                        updateArtwork(index, {
                          title: event.target.value || null,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Artist</Label>
                    <Input
                      value={artwork.artist ?? ""}
                      onChange={(event) =>
                        updateArtwork(index, {
                          artist: event.target.value || null,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Period / year</Label>
                    <Input
                      value={artwork.period_or_year ?? ""}
                      onChange={(event) =>
                        updateArtwork(index, {
                          period_or_year: event.target.value || null,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Medium</Label>
                    <Input
                      value={artwork.medium ?? ""}
                      onChange={(event) =>
                        updateArtwork(index, {
                          medium: event.target.value || null,
                        })
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Notes / observations</Label>
                  <Textarea
                    rows={3}
                    value={artwork.notes ?? ""}
                    onChange={(event) =>
                      updateArtwork(index, {
                        notes: event.target.value || null,
                      })
                    }
                  />
                </div>

                {(artwork.themes.length > 0 || artwork.concepts.length > 0) && (
                  <div className="flex flex-wrap gap-2">
                    {artwork.themes.map((theme) => (
                      <Badge key={`theme-${theme}`} variant="secondary">
                        {theme}
                      </Badge>
                    ))}
                    {artwork.concepts.map((concept) => (
                      <Badge key={`concept-${concept}`} variant="outline">
                        {concept}
                      </Badge>
                    ))}
                  </div>
                )}

                {artwork.suggested_annotations.length > 0 ? (
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        className="size-4 accent-foreground"
                        checked={artwork.saveAnnotations}
                        onChange={(event) =>
                          updateArtwork(index, {
                            saveAnnotations: event.target.checked,
                          })
                        }
                      />
                      Save suggested annotation ideas
                    </label>
                    <ul className="space-y-2">
                      {artwork.suggested_annotations.map((annotation) => (
                        <li
                          key={`${annotation.category}-${annotation.note}`}
                          className="rounded-lg bg-muted/50 px-3 py-2 text-sm text-muted-foreground"
                        >
                          <span className="font-medium text-foreground">
                            {CATEGORY_LABELS[annotation.category]}
                          </span>
                          {" — "}
                          {annotation.note}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="sm:flex-1"
              disabled={saving}
              onClick={() => setStep("paste")}
            >
              Back
            </Button>
            <Button
              type="button"
              size="touch"
              className="sm:flex-1"
              disabled={saving || !canEdit}
              onClick={() => void saveSelected()}
            >
              {saving ? "Saving…" : "Save selected entries"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
