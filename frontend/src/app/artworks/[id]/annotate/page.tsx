import { notFound } from "next/navigation";

import { AnnotationCanvas } from "@/components/annotations/annotation-canvas";
import { AnnotatePageChrome } from "@/components/annotations/annotate-page-chrome";
import { api } from "@/lib/api";
import { resolveArtworkImageUrl } from "@/lib/thumbnails";
import type { Annotation, Artwork, CulturalEntity } from "@/lib/types";

export default async function AnnotateArtworkPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const artworkId = Number(id);

  let artwork: Artwork;
  let annotations: Annotation[] = [];
  let culturalEntities: CulturalEntity[] = [];

  try {
    artwork = await api.get<Artwork>(`/api/artworks/${artworkId}`);
    annotations = await api.get<Annotation[]>(
      `/api/artworks/${artworkId}/annotations`
    );
    if (artwork.visit_id) {
      culturalEntities = await api.get<CulturalEntity[]>(
        `/api/cultural-entities?visit_id=${artwork.visit_id}`
      );
    }
  } catch {
    notFound();
  }

  return (
    <AnnotatePageChrome artwork={artwork}>
      <AnnotationCanvas
        artworkId={artwork.id}
        imageUrl={resolveArtworkImageUrl(artwork, "detail")}
        initialAnnotations={annotations}
        culturalEntities={culturalEntities}
      />
    </AnnotatePageChrome>
  );
}
