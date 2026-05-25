import { notFound } from "next/navigation";

import { ArtworkDetailClient } from "@/components/artworks/artwork-detail-client";
import { api, mediaUrl } from "@/lib/api";
import type { Annotation, Artwork, CulturalEntity } from "@/lib/types";

export default async function ArtworkDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const artworkId = Number(id);

  let artwork: Artwork;
  let annotations: Annotation[] = [];
  let culturalEntities: CulturalEntity[] = [];
  let museumName: string | null = null;

  try {
    artwork = await api.get<Artwork>(`/api/artworks/${artworkId}`);
    annotations = await api.get<Annotation[]>(
      `/api/artworks/${artworkId}/annotations`
    );
    if (artwork.visit_id) {
      const visit = await api.get<{ museum_name: string }>(`/api/visits/${artwork.visit_id}`);
      museumName = visit.museum_name;
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
      imageSrc={mediaUrl(artwork.image_url)}
      museumName={museumName}
    />
  );
}
