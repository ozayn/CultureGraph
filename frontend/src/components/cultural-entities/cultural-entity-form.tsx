"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ENTITY_TYPE_LABELS } from "@/lib/entity-types";
import type { CulturalEntity, CulturalEntityType } from "@/lib/types";

const EDITABLE_ENTITY_TYPES = Object.keys(ENTITY_TYPE_LABELS).filter(
  (type) => type !== "artwork"
) as CulturalEntityType[];

interface CulturalEntityFormProps {
  entity: CulturalEntity;
  onSuccess?: (entity: CulturalEntity) => void;
  onCancel?: () => void;
}

export function CulturalEntityForm({
  entity,
  onSuccess,
  onCancel,
}: CulturalEntityFormProps) {
  const [entityType, setEntityType] = useState(entity.entity_type);
  const [name, setName] = useState(entity.name);
  const [description, setDescription] = useState(entity.description ?? "");
  const [themes, setThemes] = useState(entity.themes.join(", "));
  const [concepts, setConcepts] = useState(entity.concepts.join(", "));
  const [movements, setMovements] = useState(entity.movements.join(", "));
  const [historicalEvents, setHistoricalEvents] = useState(
    entity.historical_events.join(", ")
  );
  const [relatedEntities, setRelatedEntities] = useState(
    entity.related_entities.join(", ")
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function splitTags(value: string): string[] {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function save() {
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const updated = await api.patch<CulturalEntity>(
        `/api/cultural-entities/${entity.id}`,
        {
          entity_type: entityType,
          name: name.trim(),
          description: description.trim() || null,
          themes: splitTags(themes),
          concepts: splitTags(concepts),
          movements: splitTags(movements),
          historical_events: splitTags(historicalEvents),
          related_entities: splitTags(relatedEntities),
        }
      );
      onSuccess?.(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save entity.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 pb-2">
      <div className="space-y-2">
        <Label htmlFor="entity_type">Type</Label>
        <select
          id="entity_type"
          value={entityType}
          onChange={(event) => setEntityType(event.target.value as CulturalEntityType)}
          className="flex h-11 w-full rounded-lg border border-input bg-background px-3 text-sm"
        >
          {EDITABLE_ENTITY_TYPES.map((type) => (
            <option key={type} value={type}>
              {ENTITY_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="entity_name">Name</Label>
        <Input
          id="entity_name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="entity_description">Description</Label>
        <Textarea
          id="entity_description"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="entity_themes">Themes</Label>
          <Input
            id="entity_themes"
            value={themes}
            onChange={(event) => setThemes(event.target.value)}
            placeholder="Comma-separated"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="entity_concepts">Concepts</Label>
          <Input
            id="entity_concepts"
            value={concepts}
            onChange={(event) => setConcepts(event.target.value)}
            placeholder="Comma-separated"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="entity_movements">Movements</Label>
          <Input
            id="entity_movements"
            value={movements}
            onChange={(event) => setMovements(event.target.value)}
            placeholder="Comma-separated"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="entity_events">Historical events</Label>
          <Input
            id="entity_events"
            value={historicalEvents}
            onChange={(event) => setHistoricalEvents(event.target.value)}
            placeholder="Comma-separated"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="entity_related">Related entities</Label>
        <Input
          id="entity_related"
          value={relatedEntities}
          onChange={(event) => setRelatedEntities(event.target.value)}
          placeholder="Comma-separated"
        />
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <div className="flex flex-col gap-2 sm:flex-row">
        {onCancel ? (
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="sm:flex-1"
            onClick={onCancel}
          >
            Cancel
          </Button>
        ) : null}
        <Button
          type="button"
          size="touch"
          className="sm:flex-1"
          disabled={loading}
          onClick={() => void save()}
        >
          {loading ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </div>
  );
}
