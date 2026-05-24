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
  personal_notes: string | null;
  created_at: string;
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
