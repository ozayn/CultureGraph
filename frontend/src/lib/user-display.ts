import type { AuthUser } from "@/contexts/auth-context";

export function getUserInitials(user: AuthUser): string {
  if (user.name?.trim()) {
    const parts = user.name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return `${parts[0][0] ?? ""}${parts[parts.length - 1][0] ?? ""}`.toUpperCase();
    }
    return parts[0]?.slice(0, 2).toUpperCase() ?? "?";
  }

  const local = user.email.split("@")[0] ?? "";
  if (!local) return "?";
  return local.slice(0, 2).toUpperCase();
}

export function getUserDisplayName(user: AuthUser): string {
  return user.name?.trim() || user.email;
}
