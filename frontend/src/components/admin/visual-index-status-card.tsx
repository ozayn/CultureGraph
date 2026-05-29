"use client";

import { format } from "date-fns";

import type { AdminVisualIndexStatus } from "@/lib/admin-types";
import { cn } from "@/lib/utils";

interface VisualIndexStatusCardProps {
  status: AdminVisualIndexStatus | null;
  loading?: boolean;
  error?: string | null;
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatTimestamp(value: string | null) {
  if (!value) return "—";
  try {
    return format(new Date(value), "MMM d, yyyy h:mm a");
  } catch {
    return value;
  }
}

export function VisualIndexStatusCard({
  status,
  loading = false,
  error = null,
}: VisualIndexStatusCardProps) {
  return (
    <section
      className={cn("rounded-xl border border-border bg-card p-4")}
      aria-labelledby="visual-index-status-heading"
    >
      <h2 id="visual-index-status-heading" className="font-heading text-lg">
        NGA visual index
      </h2>

      {loading ? (
        <p className="mt-2 text-sm text-muted-foreground">Checking visual index status…</p>
      ) : null}

      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}

      {status ? (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">indexed_count</dt>
            <dd className="mt-0.5 font-medium tabular-nums">{status.indexed_count.toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">embedding_model</dt>
            <dd className="mt-0.5 font-mono text-xs break-all">{status.embedding_model}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">last_updated</dt>
            <dd className="mt-0.5 font-medium">{formatTimestamp(status.last_updated)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">thumbnail_cache_size</dt>
            <dd className="mt-0.5 font-medium tabular-nums">
              {formatBytes(status.thumbnail_cache_size)}
            </dd>
          </div>
        </dl>
      ) : null}

      {status && status.indexed_count === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          NGA visual index is still building. Run{" "}
          <span className="font-mono">python scripts/build_nga_image_index.py --limit 500</span>{" "}
          locally to seed the first batch.
        </p>
      ) : null}
    </section>
  );
}
