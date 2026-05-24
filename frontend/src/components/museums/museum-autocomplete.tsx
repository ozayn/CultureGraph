"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { Museum } from "@/lib/types";
import { cn } from "@/lib/utils";

interface MuseumAutocompleteProps {
  id: string;
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  onMuseumSelect?: (museum: Museum) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export function MuseumAutocomplete({
  id,
  label,
  value,
  onValueChange,
  onMuseumSelect,
  placeholder = "Start typing a museum name",
  autoFocus,
}: MuseumAutocompleteProps) {
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<Museum[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);

  const fetchSuggestions = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const results = await api.get<Museum[]>(
        `/api/museums?query=${encodeURIComponent(trimmed)}`
      );
      setSuggestions(results);
      setActiveIndex(results.length > 0 ? 0 : -1);
    } catch {
      setSuggestions([]);
      setActiveIndex(-1);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;

    const handle = window.setTimeout(() => {
      void fetchSuggestions(value);
    }, 200);

    return () => window.clearTimeout(handle);
  }, [fetchSuggestions, open, value]);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  function selectMuseum(museum: Museum) {
    onValueChange(museum.name);
    onMuseumSelect?.(museum);
    setOpen(false);
    setSuggestions([]);
    setActiveIndex(-1);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      setOpen(true);
      return;
    }

    if (event.key === "Escape") {
      setOpen(false);
      return;
    }

    if (event.key === "Enter") {
      if (open && activeIndex >= 0 && suggestions[activeIndex]) {
        event.preventDefault();
        selectMuseum(suggestions[activeIndex]);
      } else {
        setOpen(false);
      }
      return;
    }

    if (!open || suggestions.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % suggestions.length);
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? suggestions.length - 1 : index - 1));
    }
  }

  const showList = open && value.trim().length > 0;
  const showEmpty = showList && !loading && suggestions.length === 0;

  return (
    <div ref={rootRef} className="relative space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={showList ? listboxId : undefined}
        aria-activedescendant={
          showList && activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
        }
        value={value}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
        onChange={(event) => {
          onValueChange(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
      />

      {showList ? (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-border bg-background shadow-sm"
        >
          {loading ? (
            <li className="px-3 py-3 text-sm text-muted-foreground">Searching museums…</li>
          ) : null}

          {!loading
            ? suggestions.map((museum, index) => (
                <li
                  key={museum.name}
                  id={`${listboxId}-option-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={cn(
                    "min-h-11 cursor-pointer border-b border-border px-3 py-2.5 last:border-b-0 active:bg-muted/70",
                    index === activeIndex && "bg-muted/50"
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectMuseum(museum)}
                >
                  <p className="text-sm font-medium">{museum.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {[museum.neighborhood, museum.city, museum.type]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </li>
              ))
            : null}

          {showEmpty ? (
            <li className="px-3 py-3 text-sm text-muted-foreground">
              No matching museum. Press Enter to use this name.
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}
