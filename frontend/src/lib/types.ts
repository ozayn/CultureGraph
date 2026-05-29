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

export type SuggestedAnnotationStatus = "pending" | "accepted" | "dismissed";

export interface AiSuggestedAnnotation {
  category: AnnotationCategory;
  note: string;
  tags: string[];
  linked_concept_names: string[];
  confidence: number;
  suggested_position: SuggestedAnnotationPosition;
  status?: SuggestedAnnotationStatus;
  accepted_annotation_id?: number | null;
}

export type AudioNoteLanguage = "en" | "fa" | "mixed" | "unknown";

export interface AudioInterpretation {
  cleaned_note: string;
  cleaned_note_original_language?: string | null;
  observations: string[];
  visual_elements: string[];
  questions: string[];
  tags: string[];
  tag_aliases?: string[];
  suggested_annotations: AiSuggestedAnnotation[];
  related_entities: string[];
}

export interface AudioNote {
  id: number;
  visit_id: number | null;
  artwork_id: number | null;
  audio_url: string;
  duration_seconds: number | null;
  transcript: string | null;
  transcript_original: string | null;
  detected_language: AudioNoteLanguage | null;
  transcript_english: string | null;
  cleaned_note: string | null;
  interpretation: AudioInterpretation | null;
  created_at: string;
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
  title: string | null;
  artist: string | null;
  year_period: string | null;
  medium: string | null;
  museum_gallery: string | null;
  image_url: string | null;
  image_master_url: string | null;
  image_thumbnail_url: string | null;
  crop_x_percent: number | null;
  crop_y_percent: number | null;
  crop_width_percent: number | null;
  crop_height_percent: number | null;
  image_width: number | null;
  image_height: number | null;
  image_mime_type: string | null;
  image_file_size: number | null;
  captured_at: string | null;
  captured_date_source: "exif" | "none";
  catalog_source: string | null;
  catalog_image_url: string | null;
  catalog_thumbnail_url: string | null;
  catalog_object_url: string | null;
  catalog_accession_number: string | null;
  catalog_rights_label: string | null;
  personal_notes: string | null;
  label_image_url: string | null;
  label_image_thumbnail_url: string | null;
  label_ocr_text: string | null;
  label_uploaded_at: string | null;
  created_at: string;
  enrichment_status?: ArtworkEnrichmentStatus;
  enrichment_stage?: ArtworkEnrichmentStage | null;
  enrichment_error?: string | null;
}

export type ArtworkEnrichmentStatus =
  | "idle"
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type ArtworkEnrichmentStage =
  | "identifying"
  | "searching_collections"
  | "generating_annotations";

export interface ArtworkEnrichmentState {
  status: ArtworkEnrichmentStatus;
  stage: ArtworkEnrichmentStage | null;
  error: string | null;
  research_note_id: number | null;
  draft: ResearchDraft | null;
  lookup: ArtworkLookupResponse | null;
  identification: ArtworkIdentification | null;
  visual_analysis: VisualAnalysis | null;
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
  medium_type?: string | null;
  medium_match?: boolean | null;
  match_reasons?: string[];
  match_tier?: "high" | "possible" | "weak";
  identity_certainty?: number | null;
  visual_similarity?: number | null;
  match_explanation?: string | null;
}

export type ArtworkLookupQuerySource =
  | "ai_title"
  | "saved_title"
  | "artist_notes"
  | "manual"
  | "ocr_label"
  | "visual_keywords";

export type ArtworkLookupQueryStrategy =
  | "semantic"
  | "exact"
  | "fuzzy"
  | "artist_fallback"
  | "broad";

export type ArtworkLookupSearchScope = "museum" | "broad" | "none";

export interface ArtworkLookupResponse {
  candidates: ArtworkLookupCandidate[];
  related_candidates?: ArtworkLookupCandidate[];
  sources_searched: string[];
  query_used: string;
  query_source: ArtworkLookupQuerySource;
  query_strategy?: ArtworkLookupQueryStrategy | null;
  artist_fallback?: boolean;
  alternate_title?: string | null;
  expected_medium_type?: string | null;
  medium_type_filter?: string;
  disclaimer: string;
  notice?: string | null;
  search_scope?: ArtworkLookupSearchScope;
  museum_collection_name?: string | null;
  retrieval_intent?: RetrievalIntent;
}

export type VisualMatchConfidenceLabel = "high" | "possible" | "weak";
export type VisualMatchIndexStatus = "ready" | "missing" | "empty";

export interface VisualMatchCandidate {
  title: string;
  artist?: string | null;
  date?: string | null;
  medium?: string | null;
  image_url?: string | null;
  thumbnail_url?: string | null;
  object_url?: string | null;
  source_name: string;
  similarity_score: number;
  confidence_label: VisualMatchConfidenceLabel;
  match_reason: string;
  accession_number?: string | null;
  rights_label?: string | null;
  external_id?: string | null;
}

export interface VisualMatchResponse {
  candidates: VisualMatchCandidate[];
  source_name?: string | null;
  museum_collection_name?: string | null;
  search_scope?: "museum" | "none";
  embedding_model?: string | null;
  notice?: string | null;
  index_status?: VisualMatchIndexStatus;
  indexed_count?: number;
  query_image_url?: string | null;
  disclaimer?: string;
}

export type ArtworkLookupMediumFilter = "2d" | "3d" | "any";

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
  visual_hypothesis_title?: string | null;
  visual_hypothesis_artist?: string | null;
  visual_hypothesis_confidence?: number | null;
  visual_hypothesis_reason?: string | null;
  hypothesis_source?: string | null;
  catalog_title?: string | null;
  catalog_artist?: string | null;
  catalog_confidence?: number | null;
  period_or_movement?: string | null;
  ocr_label_text?: string | null;
  confidence?: number | null;
  visual_analysis?: VisualAnalysis | null;
  source?: string;
}

export type IdentificationMode =
  | "catalog_match"
  | "possible_match"
  | "style_subject"
  | "exact_not_found";

export type RetrievalIntent = "standard" | "exact_artwork";
export type IdentificationConfidenceLevel = "high" | "medium" | "low";

export interface IdentityEvidence {
  exact_title_match?: boolean;
  ocr_supported?: boolean;
  artist_aligned?: boolean;
  clip_similarity?: number | null;
  reverse_image_similarity?: number | null;
  museum_context_match?: boolean;
  composition_overlap?: boolean;
  subject_overlap?: boolean;
}

export interface VisualAnalysis {
  subject?: string | null;
  composition?: string[];
  medium_clues?: string[];
  period_clues?: string[];
  clothing?: string[];
  color_palette?: string[];
  notable_objects?: string[];
  style_signals?: string[];
  movement_style?: string | null;
  performance_indicators?: string[];
  costume_clues?: string[];
  posture_gesture?: string[];
  brushwork_technique?: string[];
  framing_cropping?: string[];
  movement_depiction?: string[];
  theatrical_indicators?: string[];
  thematic_cues?: string[];
  visual_tags?: string[];
}

export interface ArtworkIdentification {
  identification_mode: IdentificationMode;
  confidence_level: IdentificationConfidenceLevel;
  display_summary: string;
  retrieval_intent?: RetrievalIntent;
  style_assessment?: string | null;
  subject_assessment?: string | null;
  iconography_notes?: string[];
  top_candidate?: ArtworkLookupCandidate | null;
  alternative_matches?: ArtworkLookupCandidate[];
  match_reasons?: string[];
  suggested_title?: string | null;
  suggested_artist?: string | null;
  visual_hypothesis_title?: string | null;
  visual_hypothesis_artist?: string | null;
  visual_hypothesis_confidence?: number | null;
  visual_hypothesis_reason?: string | null;
  hypothesis_source?: string | null;
  catalog_title?: string | null;
  catalog_artist?: string | null;
  visual_keywords?: string[];
  visual_tags?: string[];
  catalog_confidence?: number | null;
  identity_certainty?: number | null;
  visual_similarity?: number | null;
  match_explanation?: string | null;
  uncertainty_notes?: string[];
  evidence?: IdentityEvidence | null;
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
