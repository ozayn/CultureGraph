"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, MapPin, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

const tabs = [
  { href: "/", label: "Home", icon: Home },
  { href: "/visits", label: "Visits", icon: MapPin },
  { href: "/visits?new=1", label: "Add", icon: Plus },
];

export function MobileBottomNav() {
  const pathname = usePathname();
  const hide =
    pathname.includes("/annotate") || /^\/artworks\/\d+$/.test(pathname);

  if (hide) return null;

  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <div className="mx-auto grid max-w-lg grid-cols-3 gap-1 px-2 py-2">
        {tabs.map((tab) => {
          const active =
            tab.href === "/"
              ? pathname === "/"
              : tab.href.startsWith("/visits")
                ? pathname.startsWith("/visits")
                : false;
          const Icon = tab.icon;

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-lg px-2 py-1.5 text-xs transition-colors",
                active
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              )}
            >
              <Icon className="size-5" strokeWidth={1.75} />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
