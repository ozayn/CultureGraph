"use client";

import { cn } from "@/lib/utils";

export const SIGN_IN_INLINE_HINTS = {
  research: "Sign in to use AI research.",
  annotate: "Sign in to annotate.",
  upload: "Sign in to upload photos.",
  officialImage: "Sign in to find or replace official museum images.",
  note: "Sign in to add a personal note.",
  import: "Sign in to import notes.",
} as const;

export type SignInInlineHintKey = keyof typeof SIGN_IN_INLINE_HINTS;

interface SignInInlineHintProps {
  hint?: SignInInlineHintKey;
  children?: string;
  className?: string;
}

/** Lightweight hint for a locked control — not a full sign-in card. */
export function SignInInlineHint({ hint, children, className }: SignInInlineHintProps) {
  const message = children ?? (hint ? SIGN_IN_INLINE_HINTS[hint] : null);
  if (!message) return null;

  return <p className={cn("text-xs leading-relaxed text-muted-foreground", className)}>{message}</p>;
}
