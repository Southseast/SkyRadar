import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"
import { fetchLeakages, fetchStatistics, fetchTrend, patchLeakage } from "@/lib/api/results"
import { ResultsPage } from "@/pages/ResultsPage"
import type { Leakage, TrendData } from "@/types/api"

vi.mock("@/lib/api/results", () => ({
  fetchLeakages: vi.fn(),
  fetchStatistics: vi.fn(),
  fetchTrend: vi.fn(),
  patchLeakage: vi.fn(),
}))

const leakages: Leakage[] = [
  {
    _id: "leakage-1",
    link: "https://github.com/acme/skyradar/blob/main/secret.py",
    project: "acme/skyradar",
    project_url: "https://github.com/acme/skyradar",
    language: "Python",
    username: "acme",
    filepath: "secret.py",
    filename: "secret.py",
    security: 0,
    ignore: 0,
    tag: "credential",
    discovered_at: "2026-06-05T09:00:00Z",
    discovered_timestamp: 1780650000,
    datetime: "2026-06-05T08:00:00Z",
  },
  {
    _id: "leakage-2",
    link: "https://github.com/acme/ops/blob/main/env.py",
    project: "acme/ops",
    project_url: "https://github.com/acme/ops",
    language: "Python",
    username: "acme",
    filepath: "env.py",
    filename: "env.py",
    security: 0,
    ignore: 0,
    tag: "credential",
    discovered_at: "2026-06-05T09:05:00Z",
    discovered_timestamp: 1780650300,
    datetime: "2026-06-05T08:05:00Z",
  },
]

const trend: TrendData = {
  all: { total: 2, ignore: 0, risk: 0 },
  today: { total: 2, ignore: 0, risk: 0 },
  engine: { status: true, last: 1780650300 },
}

describe("ResultsPage", () => {
  beforeEach(() => {
    vi.mocked(fetchLeakages).mockReset()
    vi.mocked(fetchStatistics).mockReset()
    vi.mocked(fetchTrend).mockReset()
    vi.mocked(patchLeakage).mockReset()
    vi.mocked(fetchLeakages).mockResolvedValue({ result: leakages, total: 2 })
    vi.mocked(fetchStatistics).mockResolvedValue([])
    vi.mocked(fetchTrend).mockResolvedValue(trend)
    vi.mocked(patchLeakage).mockResolvedValue({ message: "处理成功" })
  })

  it("marks selected leakage results as ignored in batch", async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <TooltipProvider>
          <ResultsPage />
        </TooltipProvider>
      </MemoryRouter>,
    )

    await screen.findByText("acme/skyradar")
    await user.click(screen.getByRole("checkbox", { name: "选择 acme/skyradar" }))
    await user.click(screen.getByRole("checkbox", { name: "选择 acme/ops" }))
    await user.click(screen.getByRole("button", { name: "批量误报" }))

    await waitFor(() => {
      expect(patchLeakage).toHaveBeenCalledTimes(2)
    })
    expect(patchLeakage).toHaveBeenCalledWith({
      id: "leakage-1",
      project: "acme/skyradar",
      ignore: 1,
      security: 1,
      desc: "",
    })
    expect(patchLeakage).toHaveBeenCalledWith({
      id: "leakage-2",
      project: "acme/ops",
      ignore: 1,
      security: 1,
      desc: "",
    })
    expect(await screen.findByText("已批量标记 2 条为误报")).toBeInTheDocument()
  })
})
