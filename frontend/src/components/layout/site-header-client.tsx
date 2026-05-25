"use client";

import Image from "next/image";
import Link from "next/link";

import { NavbarAuthMenu } from "@/components/auth/navbar-auth-menu";
import { Separator } from "@/components/ui/separator";
import { headerNavLinkClass } from "@/lib/header-nav-styles";

export function SiteHeaderClient() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-2 px-4 sm:h-16 sm:gap-4 sm:px-6">
        <Link href="/" className="group flex min-w-0 items-center gap-2 py-1 sm:gap-3">
          <Image
            src="/icons/mark-light.svg"
            alt=""
            width={32}
            height={32}
            className="size-8 shrink-0"
            aria-hidden
          />
          <div className="min-w-0">
            <p className="font-heading text-[10px] uppercase tracking-[0.2em] text-muted-foreground sm:text-xs">
              Cultural exploration
            </p>
            <h1 className="truncate font-heading text-xl font-normal tracking-tight sm:text-2xl">
              CultureGraph
            </h1>
          </div>
        </Link>

        <div className="flex shrink-0 items-center gap-2 md:gap-4">
          <nav className="hidden items-center gap-5 text-sm md:flex">
            <Link href="/" className={headerNavLinkClass()}>
              Home
            </Link>
            <Link href="/visits" className={headerNavLinkClass()}>
              Visits
            </Link>
            <Link href="/import" className={headerNavLinkClass()}>
              Import
            </Link>
          </nav>

          <NavbarAuthMenu />
        </div>
      </div>
      <Separator className="hidden md:block" />
    </header>
  );
}
