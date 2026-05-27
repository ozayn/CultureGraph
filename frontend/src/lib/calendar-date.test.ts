import { describe, expect, it } from "vitest";

import {
  formatCalendarDate,
  isoToCalendarDate,
  parseCalendarDate,
  todayCalendarDate,
} from "@/lib/calendar-date";

describe("calendar-date", () => {
  it("parses YYYY-MM-DD without shifting the day", () => {
    expect(parseCalendarDate("2026-05-23")).toEqual({
      year: 2026,
      month: 5,
      day: 23,
    });
  });

  it("formats calendar dates in local time without UTC rollback", () => {
    expect(formatCalendarDate("2026-05-23", "MMMM d, yyyy")).toBe("May 23, 2026");
  });

  it("does not shift May 23 when using Date UTC parsing anti-pattern", () => {
    const unsafe = new Date("2026-05-23");
    const safe = formatCalendarDate("2026-05-23", "d");
    expect(safe).toBe("23");
    if (unsafe.getTimezoneOffset() > 0) {
      expect(unsafe.getDate()).not.toBe(23);
    }
  });

  it("extracts calendar date prefix from ISO datetimes", () => {
    expect(isoToCalendarDate("2026-05-23T14:30:00Z")).toBe("2026-05-23");
  });

  it("returns today as YYYY-MM-DD", () => {
    const now = new Date();
    const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    expect(todayCalendarDate()).toBe(expected);
  });
});
