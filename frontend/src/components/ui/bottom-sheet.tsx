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
  className?: string;
}

export function BottomSheet({
  open,
  onOpenChange,
  title,
  description,
  children,
  className,
}: BottomSheetProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton
        className={cn(
          "top-auto bottom-0 max-h-[88dvh] w-full max-w-none translate-x-[-50%] translate-y-0 overflow-y-auto rounded-b-none rounded-t-2xl border-b-0 p-0 sm:top-1/2 sm:bottom-auto sm:max-h-[85vh] sm:max-w-md sm:translate-y-[-50%] sm:rounded-xl sm:border-b",
          className
        )}
      >
        <DialogHeader className="sticky top-0 z-10 border-b bg-popover px-4 py-4">
          <DialogTitle className="font-heading text-lg">{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        <div className="px-4 py-4">{children}</div>
      </DialogContent>
    </Dialog>
  );
}
