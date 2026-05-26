"use client";

import { useEffect, useRef, useState } from "react";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface AdminActionsMenuProps {
  onEdit?: () => void;
  onDelete?: () => void;
  className?: string;
  label?: string;
}

export function AdminActionsMenu({
  onEdit,
  onDelete,
  className,
  label = "More actions",
}: AdminActionsMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent | TouchEvent) {
      const target = event.target as Node | null;
      if (rootRef.current && target && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  if (!onEdit && !onDelete) return null;

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((current) => !current)}
        className="inline-flex size-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:bg-muted"
      >
        <MoreHorizontal className="size-4" strokeWidth={1.75} />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-1 min-w-[9rem] overflow-hidden rounded-lg border border-border bg-popover py-1 shadow-md"
        >
          {onEdit ? (
            <button
              type="button"
              role="menuitem"
              className="flex min-h-11 w-full items-center gap-2 px-3 text-left text-sm hover:bg-muted"
              onClick={() => {
                setOpen(false);
                onEdit();
              }}
            >
              <Pencil className="size-3.5" strokeWidth={1.75} />
              Edit
            </button>
          ) : null}
          {onDelete ? (
            <button
              type="button"
              role="menuitem"
              className="flex min-h-11 w-full items-center gap-2 px-3 text-left text-sm text-destructive hover:bg-destructive/10"
              onClick={() => {
                setOpen(false);
                onDelete();
              }}
            >
              <Trash2 className="size-3.5" strokeWidth={1.75} />
              Delete
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
