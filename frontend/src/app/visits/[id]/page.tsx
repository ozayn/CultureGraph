import { notFound } from "next/navigation";

import { VisitDetailClient } from "@/components/visits/visit-detail-client";
import { api } from "@/lib/api";
import type { Artwork, Visit } from "@/lib/types";

export default async function VisitDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const visitId = Number(id);

  let visit: Visit;
  let artworks: Artwork[] = [];

  try {
    visit = await api.get<Visit>(`/api/visits/${visitId}`);
    artworks = await api.get<Artwork[]>(`/api/artworks?visit_id=${visitId}`);
  } catch {
    notFound();
  }

  return <VisitDetailClient visit={visit} artworks={artworks} />;
}
