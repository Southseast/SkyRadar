import { describe, expect, it } from "vitest"

import { formatDateTime } from "@/features/results/format"

describe("formatDateTime", () => {
  it("treats backend ISO strings without timezone as UTC", () => {
    expect(formatDateTime("2026-06-05T08:00:00")).toBe(formatDateTime("2026-06-05T08:00:00Z"))
  })

  it("returns a placeholder for empty or invalid values", () => {
    expect(formatDateTime(null)).toBe("-")
    expect(formatDateTime("not-a-date")).toBe("-")
  })
})
