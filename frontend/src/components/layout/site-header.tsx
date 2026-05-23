import Link from "next/link";

import { Separator } from "@/components/ui/separator";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3 sm:px-6 sm:py-4">
        <Link href="/" className="group min-h-11 py-1">
          <p className="font-heading text-[10px] uppercase tracking-[0.2em] text-muted-foreground sm:text-xs">
            Cultural exploration
          </p>
          <h1 className="font-heading text-xl font-normal tracking-tight sm:text-2xl">
            CultureGraph
          </h1>
        </Link>
        <nav className="hidden items-center gap-5 text-sm md:flex">
          <Link href="/" className="min-h-11 py-2 text-muted-foreground hover:text-foreground">
            Home
          </Link>
          <Link
            href="/visits"
            className="min-h-11 py-2 text-muted-foreground hover:text-foreground"
          >
            Visits
          </Link>
        </nav>
      </div>
      <Separator className="hidden md:block" />
    </header>
  );
}
