"use client";

import { User } from "lucide-react";

import type { AuthUser } from "@/contexts/auth-context";
import { getUserInitials } from "@/lib/user-display";
import { cn } from "@/lib/utils";

interface UserAvatarProps {
  user: AuthUser;
  className?: string;
  size?: "sm" | "md";
}

export function UserAvatar({ user, className, size = "md" }: UserAvatarProps) {
  const dimension = size === "sm" ? "size-8" : "size-9";
  const textSize = size === "sm" ? "text-[10px]" : "text-xs";

  if (user.picture) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={user.picture}
        alt=""
        className={cn(dimension, "rounded-full object-cover ring-1 ring-border", className)}
        referrerPolicy="no-referrer"
      />
    );
  }

  const initials = getUserInitials(user);
  if (initials && initials !== "?") {
    return (
      <span
        className={cn(
          dimension,
          textSize,
          "inline-flex items-center justify-center rounded-full bg-muted font-medium text-foreground ring-1 ring-border",
          className
        )}
        aria-hidden
      >
        {initials}
      </span>
    );
  }

  return (
    <span
      className={cn(
        dimension,
        "inline-flex items-center justify-center rounded-full bg-muted text-muted-foreground ring-1 ring-border",
        className
      )}
      aria-hidden
    >
      <User className="size-4" strokeWidth={1.75} />
    </span>
  );
}
