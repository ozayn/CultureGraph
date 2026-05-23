import Link from "next/link";

import { ButtonLink } from "@/components/ui/button-link";
import { api } from "@/lib/api";
import type { Visit } from "@/lib/types";
import { format } from "date-fns";

export default async function HomePage() {
  let visits: Visit[] = [];
  let error: string | null = null;

  try {
    visits = await api.get<Visit[]>("/api/visits");
  } catch (e) {
    error = e instanceof Error ? e.message : "Unable to reach the API.";
  }

  return (
    <div className="space-y-8 sm:space-y-10">
      <section className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground sm:text-sm">
          Reflective exploration
        </p>
        <h2 className="font-heading text-2xl font-normal leading-tight sm:text-3xl">
          Annotate artworks, log visits, connect what you see.
        </h2>
        <p className="max-w-xl text-base leading-relaxed text-muted-foreground">
          CultureGraph is a calm space for reflective exploration — notes, photos,
          pins, and AI-assisted research as you move through collections.
        </p>
        <div className="flex flex-col gap-2 pt-1 sm:flex-row sm:flex-wrap sm:gap-3">
          <ButtonLink href="/visits" className="w-full sm:w-auto">
            View visits
          </ButtonLink>
          <ButtonLink href="/visits?new=1" variant="outline" className="w-full sm:w-auto">
            Log a visit
          </ButtonLink>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-4">
          <h3 className="font-heading text-xl">Recent visits</h3>
          <Link
            href="/visits"
            className="min-h-11 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            See all
          </Link>
        </div>

        {error ? (
          <p className="rounded-xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
            {error} Start the stack with <code>scripts/dev.sh</code>.
          </p>
        ) : visits.length === 0 ? (
          <p className="text-muted-foreground">No visits yet.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {visits.slice(0, 6).map((visit) => (
              <li key={visit.id}>
                <Link
                  href={`/visits/${visit.id}`}
                  className="block min-h-11 rounded-xl border border-border bg-card p-4 transition-colors active:bg-muted/50"
                >
                  <p className="font-medium">{visit.museum_name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{visit.city}</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {format(new Date(visit.visit_date), "MMMM d, yyyy")}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
