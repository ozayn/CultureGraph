import { notFound } from "next/navigation";

import { AnnotationCanvas } from "@/components/annotations/annotation-canvas";
import { AnnotatePageChrome } from "@/components/annotations/annotate-page-chrome";
import { api, mediaUrl } from "@/lib/api";
import type { Annotation, Artwork } from "@/lib/types";

export default async function AnnotateArtworkPage({
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
    <AnnotatePageChrome artwork={artwork}>
      <AnnotationCanvas
        artworkId={artwork.id}
        imageUrl={mediaUrl(artwork.image_url)}
        initialAnnotations={annotations}
      />
    </AnnotatePageChrome>
  );
}
