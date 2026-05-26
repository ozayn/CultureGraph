"use client";

import { usePathname } from "next/navigation";

import { SiteHeaderClient } from "@/components/layout/site-header-client";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";
import { cn } from "@/lib/utils";

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAdmin = pathname.startsWith("/admin");

  return (
    <>
      <SiteHeaderClient />
      <main
        className={cn(
          "mx-auto w-full px-4 pb-24 pt-4 sm:px-6 sm:py-8 md:pb-10",
          isAdmin ? "max-w-6xl" : "max-w-3xl"
        )}
      >
        {children}
      </main>
      <MobileBottomNav />
    </>
  );
}
