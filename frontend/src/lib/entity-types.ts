import type { LucideIcon } from "lucide-react";
import {
  Clock3,
  Flag,
  Hammer,
  Landmark,
  Lightbulb,
  MapPin,
  Palette,
  Sparkles,
  User,
  Waves,
} from "lucide-react";

import type { CulturalEntityType } from "@/lib/types";

export interface EntityGroupDefinition {
  id: string;
  label: string;
  types: CulturalEntityType[];
}

export const ENTITY_GROUPS: EntityGroupDefinition[] = [
  { id: "artworks", label: "Artworks", types: ["artwork"] },
  { id: "artists", label: "Artists", types: ["artist"] },
  { id: "concepts", label: "Concepts", types: ["concept"] },
  {
    id: "techniques_materials",
    label: "Techniques & materials",
    types: ["technique", "material"],
  },
  {
    id: "historical_context",
    label: "Historical context",
    types: ["historical_event", "movement", "architecture", "museum_space"],
  },
  {
    id: "symbols_political",
    label: "Symbols & political ideas",
    types: ["symbol", "political_idea"],
  },
];

export const ENTITY_TYPE_LABELS: Record<CulturalEntityType, string> = {
  artwork: "Artwork",
  artist: "Artist",
  concept: "Concept",
  movement: "Movement",
  technique: "Technique",
  material: "Material",
  historical_event: "Historical event",
  symbol: "Symbol",
  architecture: "Architecture",
  museum_space: "Museum space",
  political_idea: "Political idea",
};

export const ENTITY_TYPE_ICONS: Record<CulturalEntityType, LucideIcon> = {
  artwork: Palette,
  artist: User,
  concept: Lightbulb,
  movement: Waves,
  technique: Hammer,
  material: Hammer,
  historical_event: Clock3,
  symbol: Sparkles,
  architecture: Landmark,
  museum_space: MapPin,
  political_idea: Flag,
};

export function groupEntities<T extends { entity_type: CulturalEntityType }>(
  entities: T[]
): Array<{ group: EntityGroupDefinition; items: T[] }> {
  const assigned = new Set<number>();

  return ENTITY_GROUPS.map((group) => {
    const items = entities.filter((entity, index) => {
      if (assigned.has(index)) return false;
      if (!group.types.includes(entity.entity_type)) return false;
      assigned.add(index);
      return true;
    });
    return { group, items };
  }).filter(({ items }) => items.length > 0);
}
