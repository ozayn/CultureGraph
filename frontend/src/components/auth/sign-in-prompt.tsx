"use client";

import { AuthGate } from "@/components/auth/auth-gate";
import { cn } from "@/lib/utils";

interface SignInPromptProps {
  className?: string;
  /** @deprecated Ignored — use AuthGate for the same lightweight layout. */
  compact?: boolean;
}

/** @deprecated Prefer AuthGate for page-level gates. */
export function SignInPrompt({ className }: SignInPromptProps) {
  return <AuthGate className={cn(className)} />;
}
