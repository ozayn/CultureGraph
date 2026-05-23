import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ButtonLinkProps = {
  href: string;
  className?: string;
  variant?: "default" | "outline" | "secondary" | "ghost" | "destructive" | "link";
  size?: "default" | "xs" | "sm" | "lg" | "touch" | "icon" | "icon-xs" | "icon-sm" | "icon-lg";
  children: React.ReactNode;
};

export function ButtonLink({
  href,
  className,
  variant = "default",
  size = "touch",
  children,
}: ButtonLinkProps) {
  return (
    <Link href={href} className={cn(buttonVariants({ variant, size }), className)}>
      {children}
    </Link>
  );
}
