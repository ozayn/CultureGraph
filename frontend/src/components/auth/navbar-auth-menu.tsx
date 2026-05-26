"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { UserAvatar } from "@/components/auth/user-avatar";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/contexts/auth-context";
import {
  headerProfileButtonClass,
  headerSignInClass,
} from "@/lib/header-nav-styles";
import { getUserDisplayName } from "@/lib/user-display";
import { cn } from "@/lib/utils";

function useIsMobileNav() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const media = window.matchMedia("(max-width: 767px)");
    const update = () => setIsMobile(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return isMobile;
}

export function NavbarAuthMenu() {
  const { canEdit, loading, signOut, user } = useAuth();
  const [signInOpen, setSignInOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobileNav();

  useEffect(() => {
    if (!menuOpen || isMobile) return;

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
  }, [isMobile, menuOpen]);

  if (loading) {
    return <div className="h-11 w-11 shrink-0" aria-hidden />;
  }

  if (!canEdit || !user) {
    return (
      <>
        <button
          type="button"
          className={headerSignInClass()}
          onClick={() => setSignInOpen(true)}
        >
          Sign in
        </button>

        {isMobile ? (
          <BottomSheet
            open={signInOpen}
            onOpenChange={setSignInOpen}
            title="Sign in"
            description="Sign in with Google to edit visits, artworks, and notes."
          >
            <GoogleSignInButton onSignedIn={() => setSignInOpen(false)} />
          </BottomSheet>
        ) : (
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
        )}
      </>
    );
  }

  const accountMenuItems = (
    <>
      <div className="border-b border-border px-1 pb-3">
        <p className="truncate text-sm font-medium text-foreground">
          {getUserDisplayName(user)}
        </p>
        {user.name ? (
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        ) : null}
      </div>
      <Link
        href="/admin"
        role="menuitem"
        className="mt-2 flex min-h-11 w-full items-center rounded-lg px-3 text-left text-sm text-foreground transition-colors hover:bg-muted"
        onClick={() => setMenuOpen(false)}
      >
        Admin dashboard
      </Link>
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
    </>
  );

  return (
    <div ref={menuRef} className="relative shrink-0">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        aria-label="Account menu"
        className={headerProfileButtonClass()}
        onClick={() => setMenuOpen((open) => !open)}
      >
        <UserAvatar user={user} />
      </button>

      {isMobile ? (
        <BottomSheet
          open={menuOpen}
          onOpenChange={setMenuOpen}
          title="Account"
          description="Manage your CultureGraph session."
        >
          {accountMenuItems}
        </BottomSheet>
      ) : menuOpen ? (
        <div
          role="menu"
          aria-label="Account"
          className={cn(
            "absolute right-0 top-[calc(100%+0.35rem)] z-50 min-w-[12rem] rounded-xl border border-border bg-popover p-2 shadow-sm",
            "animate-in fade-in-0 zoom-in-95"
          )}
        >
          {accountMenuItems}
        </div>
      ) : null}
    </div>
  );
}
