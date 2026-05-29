import { notFound } from "next/navigation";

import { ArtworkDetailClient } from "@/components/artworks/artwork-detail-client";
import { api } from "@/lib/api";
import type { Annotation, Artwork, CulturalEntity, Visit } from "@/lib/types";

export default async function ArtworkDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ enrich?: string }>;
}) {
  const { id } = await params;
  const artworkId = Number(id);

  let artwork: Artwork;
  let annotations: Annotation[] = [];
  let culturalEntities: CulturalEntity[] = [];
  let visitDate: string | null = null;
  let visitMuseumName: string | null = null;

  try {
    artwork = await api.get<Artwork>(`/api/artworks/${artworkId}`);
    annotations = await api.get<Annotation[]>(
      `/api/artworks/${artworkId}/annotations`
    );
    if (artwork.visit_id) {
      const visit = await api.get<Visit>(`/api/visits/${artwork.visit_id}`);
      visitDate = visit.visit_date;
      visitMuseumName = visit.museum_name;
      culturalEntities = await api.get<CulturalEntity[]>(
        `/api/cultural-entities?visit_id=${artwork.visit_id}`
      );
    }
  } catch {
    notFound();
  }

  return (
    <ArtworkDetailClient
      artwork={artwork}
      annotations={annotations}
      culturalEntities={culturalEntities}
      visitDate={visitDate}
      visitMuseumName={visitMuseumName}
      autoEnrich={(await searchParams).enrich === "1"}
    />
  );
}
