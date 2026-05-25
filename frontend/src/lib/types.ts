export type AnnotationCategory =
  | "observation"
  | "symbol"
  | "history"
  | "question"
  | "composition";

export interface Visit {
  id: number;
  museum_name: string;
  city: string;
  visit_date: string;
  notes: string | null;
  created_at: string;
}

export interface Museum {
  name: string;
  city: string;
  neighborhood: string | null;
  website: string | null;
  type: string | null;
}

export interface Artwork {
  id: number;
  visit_id: number | null;
  title: string;
  artist: string | null;
  year_period: string | null;
  medium: string | null;
  museum_gallery: string | null;
  image_url: string | null;
  catalog_source: string | null;
  catalog_object_url: string | null;
  catalog_accession_number: string | null;
  catalog_rights_label: string | null;
  personal_notes: string | null;
  created_at: string;
}

export interface ArtworkLookupCandidate {
  title: string;
  artist: string | null;
  date: string | null;
  medium: string | null;
  image_url: string | null;
  object_url: string | null;
  accession_number: string | null;
  source_name: string;
  confidence: number;
  rights_label: string | null;
  external_id: string | null;
}

export interface ArtworkLookupResponse {
  candidates: ArtworkLookupCandidate[];
  sources_searched: string[];
  disclaimer: string;
}

export interface Annotation {
  id: number;
  artwork_id: number;
  x_percent: number;
  y_percent: number;
  category: AnnotationCategory;
  text: string;
  created_at: string;
}

export interface ResearchDraft {
  short_summary: string;
  historical_context: string;
  visual_elements_to_notice: string[];
  related_questions: string[];
  suggested_annotations: Array<{ category: string; text: string }>;
}

export const ANNOTATION_CATEGORIES: AnnotationCategory[] = [
  "observation",
  "symbol",
  "history",
  "question",
  "composition",
];

export const CATEGORY_LABELS: Record<AnnotationCategory, string> = {
  observation: "Observation",
  symbol: "Symbol",
  history: "History",
  question: "Question",
  composition: "Composition",
};

export interface SuggestedAnnotationDraft {
  category: AnnotationCategory;
  note: string;
}

export type CulturalEntityType =
  | "artwork"
  | "artist"
  | "concept"
  | "movement"
  | "technique"
  | "material"
  | "historical_event"
  | "symbol"
  | "architecture"
  | "museum_space"
  | "political_idea";

export interface CulturalEntity {
  id: number;
  visit_id: number;
  entity_type: CulturalEntityType;
  name: string;
  description: string | null;
  themes: string[];
  concepts: string[];
  movements: string[];
  historical_events: string[];
  related_entities: string[];
  created_at: string;
}

export interface ImportedEntityDraft {
  entity_type: CulturalEntityType;
  name: string;
  description: string | null;
  related_entities: string[];
  uncertainty: string | null;
  title: string | null;
  artist: string | null;
  period_or_year: string | null;
  medium: string | null;
  display_label: string | null;
  themes: string[];
  concepts: string[];
  movements: string[];
  historical_events: string[];
  suggested_annotations: SuggestedAnnotationDraft[];
}

export interface ArtworkImportDraft {
  title: string | null;
  artist: string | null;
  period_or_year: string | null;
  medium: string | null;
  display_label: string | null;
  notes: string | null;
  themes: string[];
  concepts: string[];
  suggested_annotations: SuggestedAnnotationDraft[];
}

export interface VisitImportDraft {
  museum_name: string;
  city: string;
  visit_date: string;
  summary: string;
}

export interface ConceptLinkDraft {
  source: string;
  target: string;
  relationship: string;
}

export interface MuseumNotesImportResponse {
  visit: VisitImportDraft;
  entities: ImportedEntityDraft[];
  concept_links: ConceptLinkDraft[];
  source: string;
  ai_warning: string | null;
}
