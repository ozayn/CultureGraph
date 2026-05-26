"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface BottomSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function BottomSheet({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
}: BottomSheetProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton
        className={cn(
          "top-auto bottom-0 flex max-h-[88dvh] w-full max-w-none translate-x-[-50%] translate-y-0 flex-col overflow-hidden rounded-b-none rounded-t-2xl border-b-0 p-0 sm:top-1/2 sm:bottom-auto sm:max-h-[85vh] sm:max-w-md sm:translate-y-[-50%] sm:rounded-xl sm:border-b",
          className
        )}
      >
        <DialogHeader className="shrink-0 border-b bg-popover px-4 py-4">
          <DialogTitle className="font-heading text-lg">{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">{children}</div>
        {footer ? (
          <div
            className="shrink-0 border-t bg-popover px-4 py-4"
            style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
          >
            {footer}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
