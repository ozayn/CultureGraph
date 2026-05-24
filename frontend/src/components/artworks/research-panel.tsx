"use client";

import { useCallback, useEffect, useState } from "react";

import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ResearchDraft } from "@/lib/types";

interface ResearchPanelProps {
  artworkId: number;
  canEdit?: boolean;
  onReady?: (generate: () => Promise<void>) => void;
}

export function ResearchPanel({ artworkId, canEdit = true, onReady }: ResearchPanelProps) {
  const [draft, setDraft] = useState<ResearchDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateDraft = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.post<ResearchDraft>(
        `/api/artworks/${artworkId}/research`
      );
      setDraft(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate research.");
    } finally {
      setLoading(false);
    }
  }, [artworkId]);

  useEffect(() => {
    onReady?.(generateDraft);
  }, [generateDraft, onReady]);

  return (
    <section className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-heading text-lg">Research draft</h3>
          <p className="text-sm text-muted-foreground">
            AI-assisted context (mocked for now).
          </p>
        </div>
        <Button
          onClick={() => void generateDraft()}
          disabled={loading || !canEdit}
          variant="outline"
          size="touch"
          className="w-full sm:w-auto"
        >
          {loading ? "Generating…" : "Research with AI"}
        </Button>
      </div>

      {!canEdit ? <SignInPrompt compact className="mt-2" /> : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {draft ? (
        <div className="space-y-5 text-base leading-relaxed">
          <div>
            <h4 className="mb-1 font-medium">Summary</h4>
            <p className="text-muted-foreground">{draft.short_summary}</p>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Historical context</h4>
            <p className="text-muted-foreground">{draft.historical_context}</p>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Visual elements to notice</h4>
            <ul className="list-disc space-y-2 pl-5 text-muted-foreground">
              {draft.visual_elements_to_notice.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Related questions</h4>
            <ul className="list-disc space-y-2 pl-5 text-muted-foreground">
              {draft.related_questions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Suggested annotations</h4>
            <ul className="space-y-2">
              {draft.suggested_annotations.map((item) => (
                <li
                  key={`${item.category}-${item.text}`}
                  className="rounded-lg bg-muted/50 px-3 py-3 text-muted-foreground"
                >
                  <span className="font-medium text-foreground">{item.category}</span>
                  {" — "}
                  {item.text}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Tap Research with AI to build a draft of context and connections.
        </p>
      )}
    </section>
  );
}
