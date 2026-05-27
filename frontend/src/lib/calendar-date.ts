import { format } from "date-fns";

const CALENDAR_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

export interface CalendarDateParts {
  year: number;
  month: number;
  day: number;
}

/** Parse YYYY-MM-DD without timezone interpretation. */
export function parseCalendarDate(value: string): CalendarDateParts | null {
  const match = CALENDAR_DATE_RE.exec(value.trim());
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isFinite(year) || month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }

  const probe = new Date(year, month - 1, day);
  if (
    probe.getFullYear() !== year ||
    probe.getMonth() !== month - 1 ||
    probe.getDate() !== day
  ) {
    return null;
  }

  return { year, month, day };
}

export function isCalendarDate(value: string): boolean {
  return parseCalendarDate(value) !== null;
}

/** Local midnight for a calendar date — safe for date-fns formatting. */
export function calendarDateToLocalDate(value: string): Date | null {
  const parts = parseCalendarDate(value);
  if (!parts) return null;
  return new Date(parts.year, parts.month - 1, parts.day);
}

export function formatCalendarDate(value: string, pattern = "MMMM d, yyyy"): string {
  const date = calendarDateToLocalDate(value);
  if (!date) return value;
  return format(date, pattern);
}

/** Today's date in the user's local timezone as YYYY-MM-DD. */
export function todayCalendarDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Extract YYYY-MM-DD from an ISO datetime or date string. */
export function isoToCalendarDate(iso: string): string | null {
  const trimmed = iso.trim();
  const datePrefix = trimmed.match(/^(\d{4}-\d{2}-\d{2})/);
  if (datePrefix && isCalendarDate(datePrefix[1])) {
    return datePrefix[1];
  }
  return null;
}
