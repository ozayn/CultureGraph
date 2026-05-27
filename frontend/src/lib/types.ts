export type AnnotationCategory =
  | "observation"
  | "symbol"
  | "history"
  | "question"
  | "composition"
  | "material";

export interface SuggestedAnnotationPosition {
  x_percent: number | null;
  y_percent: number | null;
  reason: string | null;
}

export interface AiSuggestedAnnotation {
  category: AnnotationCategory;
  note: string;
  tags: string[];
  linked_concept_names: string[];
  confidence: number;
  suggested_position: SuggestedAnnotationPosition;
}

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
  image_thumbnail_url: string | null;
  image_width: number | null;
  image_height: number | null;
  image_mime_type: string | null;
  image_file_size: number | null;
  captured_at: string | null;
  captured_date_source: "exif" | "none";
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
  image_thumbnail_url: string | null;
  object_url: string | null;
  accession_number: string | null;
  source_name: string;
  confidence: number;
  rights_label: string | null;
  external_id: string | null;
  low_confidence?: boolean;
}

export type ArtworkLookupQuerySource =
  | "ai_title"
  | "saved_title"
  | "artist_notes"
  | "manual";

export type ArtworkLookupQueryStrategy =
  | "exact"
  | "fuzzy"
  | "artist_fallback"
  | "broad";

export interface ArtworkLookupResponse {
  candidates: ArtworkLookupCandidate[];
  sources_searched: string[];
  query_used: string;
  query_source: ArtworkLookupQuerySource;
  query_strategy?: ArtworkLookupQueryStrategy | null;
  artist_fallback?: boolean;
  alternate_title?: string | null;
  disclaimer: string;
  notice?: string | null;
}

export interface Annotation {
  id: number;
  artwork_id: number;
  x_percent: number | null;
  y_percent: number | null;
  category: AnnotationCategory;
  text: string;
  tags: string[];
  linked_entity_ids: number[];
  linked_concept_names: string[];
  created_at: string;
}

export interface ResearchDraft {
  short_summary: string;
  historical_context: string;
  visual_elements_to_notice: string[];
  related_questions: string[];
  suggested_annotations: AiSuggestedAnnotation[];
  possible_title?: string | null;
  possible_artist?: string | null;
  period_or_movement?: string | null;
  ocr_label_text?: string | null;
  confidence?: number | null;
  source?: string;
}

export interface ResearchNote {
  id: number;
  artwork_id: number;
  short_summary: string;
  historical_context: string;
  visual_elements_to_notice: string;
  related_questions: string;
  suggested_annotations: string;
  possible_title?: string | null;
  possible_artist?: string | null;
  period_or_movement?: string | null;
  created_at: string;
}

export const ANNOTATION_CATEGORIES: AnnotationCategory[] = [
  "observation",
  "symbol",
  "history",
  "question",
  "composition",
  "material",
];

export const CATEGORY_LABELS: Record<AnnotationCategory, string> = {
  observation: "Observation",
  symbol: "Symbol",
  history: "History",
  question: "Question",
  composition: "Composition",
  material: "Material",
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
  image_url: string | null;
  thumbnail_url: string | null;
  image_source_name: string | null;
  image_source_url: string | null;
  image_rights_label: string | null;
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
  image_url?: string | null;
  thumbnail_url?: string | null;
  image_source_name?: string | null;
  image_source_url?: string | null;
  image_rights_label?: string | null;
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
