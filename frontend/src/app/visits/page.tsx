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
  let error: string | null = null;

  try {
    visits = await api.get<Visit[]>("/api/visits");
  } catch (e) {
    error = e instanceof Error ? e.message : "Unable to reach the API.";
  }

  return (
    <VisitsPageClient visits={visits} showForm={params.new === "1"} error={error} />
  );
}
