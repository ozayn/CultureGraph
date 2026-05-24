"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

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
  ENTITY_TYPE_ICONS,
  ENTITY_TYPE_LABELS,
  groupEntities,
} from "@/lib/entity-types";
import {
  CATEGORY_LABELS,
  type ImportedEntityDraft,
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
Leonardo Drew — found objects, weathered wood and rust
WPA mural program in the rotunda
Gesso ground on unprimed canvas
DC Color School — local color abstraction
Clenched fist motif in protest prints
Lincoln Gallery — east wing sculpture corridor`;

type ImportStep = "paste" | "review";

interface ReviewEntity extends ImportedEntityDraft {
  selected: boolean;
  saveAnnotations: boolean;
}

function buildPersonalNotes(entity: ReviewEntity): string | null {
  const parts: string[] = [];
  if (entity.description?.trim()) parts.push(entity.description.trim());
  if (entity.themes.length) parts.push(`Themes: ${entity.themes.join(", ")}`);
  if (entity.concepts.length) parts.push(`Concepts: ${entity.concepts.join(", ")}`);
  if (entity.movements.length) parts.push(`Movements: ${entity.movements.join(", ")}`);
  if (entity.historical_events.length) {
    parts.push(`Historical events: ${entity.historical_events.join(", ")}`);
  }
  if (entity.related_entities.length) {
    parts.push(`Related: ${entity.related_entities.join(", ")}`);
  }
  if (entity.uncertainty?.trim()) parts.push(`Uncertainty: ${entity.uncertainty.trim()}`);
  return parts.length ? parts.join("\n\n") : null;
}

function formatConceptLinks(links: MuseumNotesImportResponse["concept_links"]): string {
  return links
    .map((link) => `${link.source} → ${link.target} (${link.relationship})`)
    .join("\n");
}

function formatEntityForVisitNotes(entity: ReviewEntity): string {
  const label = ENTITY_TYPE_LABELS[entity.entity_type];
  const body = entity.description?.trim() || entity.name;
  const related =
    entity.related_entities.length > 0
      ? ` Related: ${entity.related_entities.join(", ")}.`
      : "";
  return `- [${label}] ${entity.name} — ${body}${related}`;
}

function EntityTypeChip({ entityType }: { entityType: ReviewEntity["entity_type"] }) {
  const Icon = ENTITY_TYPE_ICONS[entityType];
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground">
      <Icon className="size-3" strokeWidth={1.75} />
      {ENTITY_TYPE_LABELS[entityType]}
    </span>
  );
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
  const [entities, setEntities] = useState<ReviewEntity[]>([]);
  const [source, setSource] = useState<string>("mock");
  const [aiWarning, setAiWarning] = useState<string | null>(null);

  const groupedEntities = useMemo(() => groupEntities(entities), [entities]);

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
      setAiWarning(result.ai_warning ?? null);
      setEntities(
        result.entities.map((entity) => ({
          ...entity,
          selected: true,
          saveAnnotations: true,
        }))
      );
      setMuseumName(result.visit.museum_name);
      setCity(result.visit.city);
      setVisitDate(result.visit.visit_date);
      setStep("review");
    } catch (e) {
      const message = e instanceof Error ? e.message : "Could not extract entries.";
      if (message.includes("unexpected shape") || message.includes("could not be parsed")) {
        setError(
          "AI extraction returned an unexpected shape. Try again or use local fallback."
        );
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }

  function updateEntity(index: number, patch: Partial<ReviewEntity>) {
    setEntities((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item))
    );
  }

  async function saveSelected() {
    if (!canEdit) {
      setError("Sign in to edit CultureGraph.");
      return;
    }
    const selectedEntities = entities.filter((entity) => entity.selected);
    const selectedArtworks = selectedEntities.filter((entity) => entity.entity_type === "artwork");
    const selectedOther = selectedEntities.filter((entity) => entity.entity_type !== "artwork");

    if (!saveVisit && selectedArtworks.length === 0 && selectedOther.length === 0) {
      setError("Select a visit and/or at least one entry to save.");
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
        const culturalSection =
          selectedOther.length > 0
            ? `\n\nExtracted entries:\n${selectedOther.map(formatEntityForVisitNotes).join("\n")}`
            : "";
        const visitNotes = [visitSummary.trim(), conceptSection.trim(), culturalSection.trim()]
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

      for (const entity of selectedArtworks) {
        const saved = await api.post<{ id: number }>("/api/artworks", {
          title: entity.title?.trim() || entity.name.trim() || "Untitled artwork",
          artist: entity.artist?.trim() || null,
          year_period: entity.period_or_year?.trim() || null,
          medium: entity.medium?.trim() || null,
          personal_notes: buildPersonalNotes(entity),
          visit_id: visitId,
        });

        if (entity.saveAnnotations) {
          for (const annotation of entity.suggested_annotations) {
            await api.post(`/api/artworks/${saved.id}/annotations`, {
              x_percent: 50,
              y_percent: 50,
              category: annotation.category,
              text: annotation.note,
            });
          }
        }
      }

      router.push(visitId ? `/visits/${visitId}` : "/visits");
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
          Paste a tour outline, gallery walk, or ChatGPT summary. CultureGraph classifies artworks,
          artists, concepts, techniques, and other cultural entries for you to review before saving.
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

          {aiWarning ? (
            <p className="rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              AI extraction needed cleanup; please review carefully.
            </p>
          ) : null}

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
                  Save as a visit record with summary and cultural entries
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

          <div className="space-y-6">
            <div className="space-y-1">
              <h3 className="font-heading text-xl">Extracted entries</h3>
              <p className="text-sm text-muted-foreground">
                {entities.filter((entity) => entity.selected).length} of {entities.length} selected
              </p>
            </div>

            {groupedEntities.map(({ group, items }) => (
              <section key={group.id} className="space-y-3">
                <h4 className="text-sm uppercase tracking-[0.14em] text-muted-foreground">
                  {group.label}
                </h4>
                {items.map((entity) => {
                  const index = entities.indexOf(entity);
                  return (
                    <article
                      key={`${entity.entity_type}-${entity.name}-${index}`}
                      className={cn(
                        "space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5",
                        !entity.selected && "opacity-60"
                      )}
                    >
                      <label className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          className="mt-1 size-4 shrink-0 accent-foreground"
                          checked={entity.selected}
                          onChange={(event) =>
                            updateEntity(index, { selected: event.target.checked })
                          }
                        />
                        <span className="min-w-0 flex-1 space-y-2">
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="font-heading text-lg">{entity.name}</span>
                            <EntityTypeChip entityType={entity.entity_type} />
                          </span>
                          {entity.description ? (
                            <span className="block text-sm leading-relaxed text-muted-foreground">
                              {entity.description}
                            </span>
                          ) : null}
                        </span>
                      </label>

                      {entity.entity_type === "artwork" ? (
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          <div className="space-y-2">
                            <Label>Title</Label>
                            <Input
                              value={entity.title ?? ""}
                              placeholder="Unknown — edit or leave blank"
                              onChange={(event) =>
                                updateEntity(index, {
                                  title: event.target.value || null,
                                  name: event.target.value || entity.name,
                                })
                              }
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Artist</Label>
                            <Input
                              value={entity.artist ?? ""}
                              onChange={(event) =>
                                updateEntity(index, {
                                  artist: event.target.value || null,
                                })
                              }
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Period / year</Label>
                            <Input
                              value={entity.period_or_year ?? ""}
                              onChange={(event) =>
                                updateEntity(index, {
                                  period_or_year: event.target.value || null,
                                })
                              }
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Medium</Label>
                            <Input
                              value={entity.medium ?? ""}
                              onChange={(event) =>
                                updateEntity(index, {
                                  medium: event.target.value || null,
                                })
                              }
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <Label>Description</Label>
                          <Textarea
                            rows={2}
                            value={entity.description ?? ""}
                            onChange={(event) =>
                              updateEntity(index, {
                                description: event.target.value || null,
                              })
                            }
                          />
                        </div>
                      )}

                      {(entity.themes.length > 0 ||
                        entity.concepts.length > 0 ||
                        entity.movements.length > 0 ||
                        entity.historical_events.length > 0 ||
                        entity.related_entities.length > 0) && (
                        <div className="flex flex-wrap gap-2">
                          {entity.themes.map((theme) => (
                            <Badge key={`theme-${theme}`} variant="secondary">
                              {theme}
                            </Badge>
                          ))}
                          {entity.concepts.map((concept) => (
                            <Badge key={`concept-${concept}`} variant="outline">
                              {concept}
                            </Badge>
                          ))}
                          {entity.movements.map((movement) => (
                            <Badge key={`movement-${movement}`} variant="outline">
                              {movement}
                            </Badge>
                          ))}
                          {entity.historical_events.map((eventName) => (
                            <Badge key={`event-${eventName}`} variant="outline">
                              {eventName}
                            </Badge>
                          ))}
                          {entity.related_entities.map((related) => (
                            <Badge key={`related-${related}`} variant="secondary">
                              → {related}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {entity.uncertainty ? (
                        <p className="text-xs text-muted-foreground">{entity.uncertainty}</p>
                      ) : null}

                      {entity.entity_type === "artwork" &&
                      entity.suggested_annotations.length > 0 ? (
                        <div className="space-y-2">
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              className="size-4 accent-foreground"
                              checked={entity.saveAnnotations}
                              onChange={(event) =>
                                updateEntity(index, {
                                  saveAnnotations: event.target.checked,
                                })
                              }
                            />
                            Save suggested annotation ideas
                          </label>
                          <ul className="space-y-2">
                            {entity.suggested_annotations.map((annotation) => (
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
                  );
                })}
              </section>
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
