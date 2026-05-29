"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
import type { ArtworkEnrichmentState, ArtworkEnrichmentStatus } from "@/lib/types";

export const ENRICHMENT_POLL_INTERVAL_MS = 4_000;
export const ENRICHMENT_MAX_POLL_DURATION_MS = 5 * 60 * 1_000;

export function isEnrichmentActive(
  status: ArtworkEnrichmentStatus | null | undefined
): boolean {
  return status === "pending" || status === "running";
}

type Listener = () => void;

interface EnrichmentSnapshot {
  state: ArtworkEnrichmentState | null;
  loading: boolean;
  error: string | null;
}

interface EnrichmentEntry {
  artworkId: number;
  snapshot: EnrichmentSnapshot;
  listeners: Set<Listener>;
  subscriberCount: number;
  pollTimer: ReturnType<typeof setInterval> | null;
  pollStartedAt: number | null;
  inFlight: Promise<ArtworkEnrichmentState | null> | null;
}

const entries = new Map<number, EnrichmentEntry>();
let visibilityListenerAttached = false;

function emptySnapshot(): EnrichmentSnapshot {
  return { state: null, loading: false, error: null };
}

function notify(entry: EnrichmentEntry) {
  for (const listener of entry.listeners) {
    listener();
  }
}

function getEntry(artworkId: number): EnrichmentEntry {
  let entry = entries.get(artworkId);
  if (!entry) {
    entry = {
      artworkId,
      snapshot: emptySnapshot(),
      listeners: new Set(),
      subscriberCount: 0,
      pollTimer: null,
      pollStartedAt: null,
      inFlight: null,
    };
    entries.set(artworkId, entry);
  }
  return entry;
}

function stopPolling(entry: EnrichmentEntry) {
  if (entry.pollTimer != null) {
    clearInterval(entry.pollTimer);
    entry.pollTimer = null;
  }
  entry.pollStartedAt = null;
}

function shouldPoll(entry: EnrichmentEntry): boolean {
  return (
    entry.subscriberCount > 0 &&
    typeof document !== "undefined" &&
    !document.hidden &&
    isEnrichmentActive(entry.snapshot.state?.status)
  );
}

function syncPolling(entry: EnrichmentEntry) {
  if (!shouldPoll(entry)) {
    stopPolling(entry);
    return;
  }

  if (entry.pollTimer != null) {
    return;
  }

  entry.pollStartedAt = Date.now();
  entry.pollTimer = setInterval(() => {
    if (!shouldPoll(entry)) {
      syncPolling(entry);
      return;
    }

    if (
      entry.pollStartedAt != null &&
      Date.now() - entry.pollStartedAt > ENRICHMENT_MAX_POLL_DURATION_MS
    ) {
      stopPolling(entry);
      return;
    }

    void refreshEnrichmentEntry(entry.artworkId);
  }, ENRICHMENT_POLL_INTERVAL_MS);
}

function attachVisibilityListener() {
  if (visibilityListenerAttached || typeof document === "undefined") {
    return;
  }

  visibilityListenerAttached = true;
  document.addEventListener("visibilitychange", () => {
    for (const entry of entries.values()) {
      syncPolling(entry);
    }
  });
}

async function refreshEnrichmentEntry(
  artworkId: number
): Promise<ArtworkEnrichmentState | null> {
  const entry = getEntry(artworkId);
  if (entry.inFlight) {
    return entry.inFlight;
  }

  entry.snapshot = { ...entry.snapshot, loading: entry.snapshot.state == null };
  notify(entry);

  entry.inFlight = (async () => {
    try {
      const next = await api.get<ArtworkEnrichmentState>(
        `/api/artworks/${artworkId}/enrichment`
      );
      entry.snapshot = {
        state: next,
        loading: false,
        error: next.error,
      };
      notify(entry);
      syncPolling(entry);
      return next;
    } catch (error) {
      entry.snapshot = {
        ...entry.snapshot,
        loading: false,
        error: error instanceof Error ? error.message : "Could not load AI enrichment.",
      };
      notify(entry);
      syncPolling(entry);
      return null;
    } finally {
      entry.inFlight = null;
    }
  })();

  return entry.inFlight;
}

async function startEnrichmentEntry(
  artworkId: number,
  broadenSearch = false
): Promise<ArtworkEnrichmentState | null> {
  try {
    const query = broadenSearch ? "?broaden_search=true" : "";
    await api.post(`/api/artworks/${artworkId}/enrichment${query}`);
  } catch {
    // Upload handler may have already queued enrichment.
  }

  return refreshEnrichmentEntry(artworkId);
}

function subscribeToEnrichmentEntry(
  artworkId: number,
  listener: Listener,
  enabled: boolean
): () => void {
  const entry = getEntry(artworkId);
  entry.listeners.add(listener);

  if (enabled) {
    entry.subscriberCount += 1;
    attachVisibilityListener();
    if (entry.snapshot.state == null && !entry.inFlight) {
      void refreshEnrichmentEntry(artworkId);
    }
    syncPolling(entry);
  }

  return () => {
    entry.listeners.delete(listener);
    if (enabled) {
      entry.subscriberCount = Math.max(0, entry.subscriberCount - 1);
      syncPolling(entry);

      if (entry.subscriberCount === 0) {
        stopPolling(entry);
      }
    }
  };
}

function getEnrichmentSnapshot(artworkId: number): EnrichmentSnapshot {
  return getEntry(artworkId).snapshot;
}

export interface UseArtworkEnrichmentOptions {
  artworkId: number;
  /** When false, skips polling/subscription (e.g. artwork page not active). */
  enabled?: boolean;
}

export function useArtworkEnrichment({
  artworkId,
  enabled = true,
}: UseArtworkEnrichmentOptions) {
  const subscribe = useCallback(
    (listener: Listener) => subscribeToEnrichmentEntry(artworkId, listener, enabled),
    [artworkId, enabled]
  );

  const getSnapshot = useCallback(
    () => getEnrichmentSnapshot(artworkId),
    [artworkId]
  );

  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const refresh = useCallback(
    () => refreshEnrichmentEntry(artworkId),
    [artworkId]
  );

  const startEnrichment = useCallback(
    (broadenSearch = false) => startEnrichmentEntry(artworkId, broadenSearch),
    [artworkId]
  );

  return {
    state: snapshot.state,
    loading: snapshot.loading,
    error: snapshot.error,
    isActive: isEnrichmentActive(snapshot.state?.status),
    refresh,
    startEnrichment,
  };
}

/** Test-only reset for module-level enrichment store. */
export function resetArtworkEnrichmentStoreForTests() {
  for (const entry of entries.values()) {
    stopPolling(entry);
  }
  entries.clear();
}
