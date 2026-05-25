import { cn } from "@/lib/utils";

/** Shared height and typography for header nav links and auth actions. */
export const headerNavItemClass =
  "inline-flex h-11 shrink-0 items-center text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 rounded-lg";

export function headerNavLinkClass(className?: string) {
  return cn(headerNavItemClass, className);
}

export function headerSignInClass(className?: string) {
  return cn(
    headerNavItemClass,
    "border border-transparent px-4 hover:bg-muted/40",
    className
  );
}

export function headerProfileButtonClass(className?: string) {
  return cn(
    headerNavItemClass,
    "size-11 justify-center rounded-full p-0 hover:bg-muted/60",
    className
  );
}
