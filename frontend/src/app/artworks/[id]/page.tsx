import Image from "next/image";
import { notFound } from "next/navigation";

import { ButtonLink } from "@/components/ui/button-link";
import { api, mediaUrl } from "@/lib/api";
import type { Artwork } from "@/lib/types";

export default async function ArtworkDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let artwork: Artwork;
  try {
    artwork = await api.get<Artwork>(`/api/artworks/${Number(id)}`);
  } catch {
    notFound();
  }

  const imageSrc = mediaUrl(artwork.image_url);

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="font-heading text-3xl font-normal">{artwork.title}</h1>
        <p className="text-muted-foreground">
          {[artwork.artist, artwork.year_period, artwork.museum_gallery]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {artwork.personal_notes ? (
          <p className="leading-relaxed text-muted-foreground">{artwork.personal_notes}</p>
        ) : null}
      </section>
      {imageSrc ? (
        <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-border bg-[#f3efe8]">
          <Image src={imageSrc} alt={artwork.title} fill className="object-contain" unoptimized />
        </div>
      ) : null}
      <ButtonLink href={`/artworks/${artwork.id}/annotate`} variant="outline">
        Annotate
      </ButtonLink>
    </div>
  );
}
