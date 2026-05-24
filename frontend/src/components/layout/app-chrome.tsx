"use client";

import { SiteHeaderClient } from "@/components/layout/site-header-client";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";

export function AppChrome({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteHeaderClient />
      <main className="mx-auto w-full max-w-3xl px-4 pb-24 pt-4 sm:px-6 sm:py-8 md:pb-10">
        {children}
      </main>
      <MobileBottomNav />
    </>
  );
}
