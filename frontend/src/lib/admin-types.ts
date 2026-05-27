export interface AdminSummary {
  visits: number;
  artworks: number;
  annotations: number;
  cultural_entities: number;
  research_notes: number;
}

export interface AdminListMeta {
  total: number;
  limit: number;
  offset: number;
  search: string | null;
}

export interface AdminPaginated<T> {
  records: T[];
  meta: AdminListMeta;
}

export interface AdminVisitRecord {
  id: number;
  museum_name: string;
  city: string;
  visit_date: string;
  notes: string | null;
  created_at: string;
}

export interface AdminArtworkRecord {
  id: number;
  visit_id: number | null;
  title: string;
  artist: string | null;
  year_period: string | null;
  image_url: string | null;
  image_thumbnail_url: string | null;
  catalog_image_url?: string | null;
  catalog_thumbnail_url?: string | null;
  catalog_source: string | null;
  created_at: string;
}

export interface AdminAnnotationRecord {
  id: number;
  artwork_id: number;
  category: string;
  text: string;
  x_percent: number | null;
  y_percent: number | null;
  created_at: string;
}

export interface AdminEntityRecord {
  id: number;
  visit_id: number;
  entity_type: string;
  name: string;
  description: string | null;
  image_url: string | null;
  thumbnail_url: string | null;
  created_at: string;
}

export interface AdminResearchNoteRecord {
  id: number;
  artwork_id: number;
  short_summary: string;
  created_at: string;
}

export type AdminTab =
  | "visits"
  | "artworks"
  | "annotations"
  | "entities"
  | "research-notes";

export const ADMIN_TAB_LABELS: Record<AdminTab, string> = {
  visits: "Visits",
  artworks: "Artworks",
  annotations: "Annotations",
  entities: "Entities / Concepts",
  "research-notes": "Research Notes",
};

export const ADMIN_TAB_PATHS: Record<AdminTab, string> = {
  visits: "/api/admin/visits",
  artworks: "/api/admin/artworks",
  annotations: "/api/admin/annotations",
  entities: "/api/admin/entities",
  "research-notes": "/api/admin/research-notes",
};

export const ADMIN_TAB_BULK_DELETE_PATHS: Record<AdminTab, string> = {
  visits: "/api/admin/visits/bulk-delete",
  artworks: "/api/admin/artworks/bulk-delete",
  annotations: "/api/admin/annotations/bulk-delete",
  entities: "/api/admin/entities/bulk-delete",
  "research-notes": "/api/admin/research-notes/bulk-delete",
};

export interface AdminBulkDeleteResponse {
  deleted_count: number;
}
