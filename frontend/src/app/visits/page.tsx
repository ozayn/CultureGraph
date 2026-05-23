import { VisitsPageClient } from "@/components/visits/visits-page-client";
import { api } from "@/lib/api";
import type { Visit } from "@/lib/types";

export default async function VisitsPage({
  searchParams,
}: {
  searchParams: Promise<{ new?: string }>;
}) {
  const params = await searchParams;
  let visits: Visit[] = [];

  try {
    visits = await api.get<Visit[]>("/api/visits");
  } catch {
    visits = [];
  }

  return <VisitsPageClient visits={visits} showForm={params.new === "1"} />;
}
