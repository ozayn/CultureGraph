"use client";

import { useState } from "react";

import { MuseumAutocomplete } from "@/components/museums/museum-autocomplete";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { Visit } from "@/lib/types";

interface VisitFormProps {
  visit?: Visit;
  onSuccess?: (visit: Visit) => void;
  compact?: boolean;
  redirectOnSave?: boolean;
}

export function VisitForm({
  visit,
  onSuccess,
  compact,
  redirectOnSave = !visit,
}: VisitFormProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [museumName, setMuseumName] = useState(visit?.museum_name ?? "");
  const [city, setCity] = useState(visit?.city ?? "");
  const [visitDate, setVisitDate] = useState(
    visit?.visit_date ?? new Date().toISOString().slice(0, 10)
  );
  const [notes, setNotes] = useState(visit?.notes ?? "");

  async function saveVisit(includeNotes: boolean) {
    if (!museumName.trim() || !city.trim() || !visitDate) {
      setError("Museum, city, and date are required.");
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      museum_name: museumName.trim(),
      city: city.trim(),
      visit_date: visitDate,
      notes: includeNotes && notes.trim() ? notes.trim() : null,
    };

    try {
      const saved = visit
        ? await api.put<Visit>(`/api/visits/${visit.id}`, payload)
        : await api.post<Visit>("/api/visits", payload);

      onSuccess?.(saved);
      if (redirectOnSave) {
        window.location.href = `/visits/${saved.id}`;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save visit.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={compact ? "space-y-4" : "space-y-5"}>
      <p className="text-sm text-muted-foreground">
        Step {step} of 2 · {step === 1 ? "Where & when" : "Optional notes"}
      </p>

      {step === 1 ? (
        <div className="space-y-4">
          <MuseumAutocomplete
            id="museum_name"
            label="Museum"
            value={museumName}
            onValueChange={setMuseumName}
            onMuseumSelect={(museum) => setCity(museum.city)}
            placeholder="National Gallery of Art"
            autoFocus
          />
          <div className="space-y-2">
            <Label htmlFor="city">City</Label>
            <Input
              id="city"
              value={city}
              onChange={(event) => setCity(event.target.value)}
              placeholder="Washington, DC"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="visit_date">Visit date</Label>
            <Input
              id="visit_date"
              type="date"
              value={visitDate}
              onChange={(event) => setVisitDate(event.target.value)}
            />
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <Label htmlFor="notes">Notes</Label>
          <Textarea
            id="notes"
            rows={4}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="What wing are you starting in?"
          />
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
              disabled={loading}
              onClick={() => setStep(2)}
            >
              Add notes
            </Button>
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="sm:flex-1"
              disabled={loading}
              onClick={() => saveVisit(false)}
            >
              {loading ? "Saving…" : "Save visit"}
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
              onClick={() => saveVisit(false)}
            >
              Skip notes
            </Button>
            <Button
              type="button"
              size="touch"
              className="sm:flex-1"
              disabled={loading}
              onClick={() => saveVisit(true)}
            >
              {loading ? "Saving…" : "Save visit"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
