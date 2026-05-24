"use client";

import Link from "next/link";
import { format } from "date-fns";

import { VisitForm } from "@/components/visits/visit-form";
import type { Visit } from "@/lib/types";

interface VisitsPageClientProps {
  visits: Visit[];
  showForm?: boolean;
  error?: string | null;
}

export function VisitsPageClient({ visits, showForm, error }: VisitsPageClientProps) {
  return (
    <div className="space-y-8 sm:space-y-10">
      <section className="space-y-2">
        <h2 className="font-heading text-2xl font-normal sm:text-3xl">Visits</h2>
        <p className="text-base text-muted-foreground">
          A chronological record of museum visits and saved works.
        </p>
      </section>

      {showForm !== false ? (
        <section className="rounded-xl border border-border bg-card p-4 sm:p-5">
          <h3 className="mb-4 font-heading text-xl">Log a visit</h3>
          <VisitForm compact />
        </section>
      ) : null}

      <section className="space-y-3">
        <h3 className="font-heading text-xl">All visits</h3>
        {error ? (
          <p className="rounded-xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
            {error} Check <code>NEXT_PUBLIC_API_URL</code> and that the API is running.
          </p>
        ) : visits.length === 0 ? (
          <p className="text-muted-foreground">No visits recorded yet.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {visits.map((visit) => (
              <li key={visit.id}>
                <Link
                  href={`/visits/${visit.id}`}
                  className="block min-h-11 rounded-xl border border-border bg-card p-4 transition-colors active:bg-muted/50"
                >
                  <p className="font-medium">{visit.museum_name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {visit.city} · {format(new Date(visit.visit_date), "MMMM d, yyyy")}
                  </p>
                  {visit.notes ? (
                    <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                      {visit.notes}
                    </p>
                  ) : null}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
