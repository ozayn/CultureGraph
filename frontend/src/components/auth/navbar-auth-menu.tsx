"use client";

import { useEffect, useRef, useState } from "react";

import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { UserAvatar } from "@/components/auth/user-avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/contexts/auth-context";
import { getUserDisplayName } from "@/lib/user-display";
import { cn } from "@/lib/utils";

export function NavbarAuthMenu() {
  const { canEdit, loading, signOut, user } = useAuth();
  const [signInOpen, setSignInOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;

    function handlePointerDown(event: MouseEvent | TouchEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  if (loading) {
    return <div className="size-11 shrink-0" aria-hidden />;
  }

  if (!canEdit || !user) {
    return (
      <>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="min-h-11 px-3 text-sm text-muted-foreground hover:text-foreground"
          onClick={() => setSignInOpen(true)}
        >
          Sign in
        </Button>

        <Dialog open={signInOpen} onOpenChange={setSignInOpen}>
          <DialogContent showCloseButton className="sm:max-w-sm">
            <DialogHeader>
              <DialogTitle>Sign in</DialogTitle>
              <DialogDescription>
                Sign in with Google to edit visits, artworks, and notes.
              </DialogDescription>
            </DialogHeader>
            <GoogleSignInButton onSignedIn={() => setSignInOpen(false)} />
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <div ref={menuRef} className="relative shrink-0">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        aria-label="Account menu"
        className="flex size-11 items-center justify-center rounded-full transition-colors hover:bg-muted/60"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <UserAvatar user={user} />
      </button>

      {menuOpen ? (
        <div
          role="menu"
          aria-label="Account"
          className={cn(
            "absolute right-0 top-[calc(100%+0.35rem)] z-50 min-w-[12rem] rounded-xl border border-border bg-popover p-2 shadow-sm",
            "animate-in fade-in-0 zoom-in-95"
          )}
        >
          <div className="border-b border-border px-3 py-2.5">
            <p className="truncate text-sm font-medium text-foreground">
              {getUserDisplayName(user)}
            </p>
            {user.name ? (
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            ) : null}
          </div>
          <button
            type="button"
            role="menuitem"
            className="mt-1 flex min-h-11 w-full items-center rounded-lg px-3 text-left text-sm text-foreground transition-colors hover:bg-muted"
            onClick={() => {
              signOut();
              setMenuOpen(false);
            }}
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
