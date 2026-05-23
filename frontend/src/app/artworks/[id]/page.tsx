import { notFound } from "next/navigation";

import { ArtworkDetailClient } from "@/components/artworks/artwork-detail-client";
import { api, mediaUrl } from "@/lib/api";
import type { Annotation, Artwork } from "@/lib/types";

export default async function ArtworkDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const artworkId = Number(id);

  let artwork: Artwork;
  let annotations: Annotation[] = [];

  try {
    artwork = await api.get<Artwork>(`/api/artworks/${artworkId}`);
    annotations = await api.get<Annotation[]>(
      `/api/artworks/${artworkId}/annotations`
    );
  } catch {
    notFound();
  }

  return (
    <ArtworkDetailClient
      artwork={artwork}
      annotations={annotations}
      imageSrc={mediaUrl(artwork.image_url)}
    />
  );
}
