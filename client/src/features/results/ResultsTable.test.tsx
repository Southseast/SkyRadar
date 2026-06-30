import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"
import { ResultsTable } from "@/features/results/ResultsTable"
import type { Leakage } from "@/types/api"

const leakage: Leakage = {
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
}

describe("ResultsTable", () => {
  it("renders separate actions for leakage detail code and GitHub source", () => {
    render(
      <MemoryRouter>
        <TooltipProvider>
          <ResultsTable
            results={[leakage]}
            loading={false}
            onMarkIgnored={vi.fn()}
            selectedIds={new Set()}
            onToggleSelection={vi.fn()}
            onTogglePageSelection={vi.fn()}
          />
        </TooltipProvider>
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: "查看泄露详情代码" })).toHaveAttribute("href", "/view/leakage/leakage-1")
    expect(screen.getByRole("link", { name: "GitHub 源代码" })).toHaveAttribute(
      "href",
      "https://github.com/acme/skyradar/blob/main/secret.py",
    )
  })

  it("keeps repository and file labels as static text", () => {
    render(
      <MemoryRouter>
        <TooltipProvider>
          <ResultsTable
            results={[leakage]}
            loading={false}
            onMarkIgnored={vi.fn()}
            selectedIds={new Set()}
            onToggleSelection={vi.fn()}
            onTogglePageSelection={vi.fn()}
          />
        </TooltipProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText("发现时间")).toBeInTheDocument()
    expect(screen.getByText("更新时间")).toBeInTheDocument()
    expect(screen.getByText("仓库")).toBeInTheDocument()
    expect(screen.getByText("文件")).toBeInTheDocument()
    expect(screen.getByText("acme/skyradar")).toBeInTheDocument()
    expect(screen.getByText("secret.py")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "acme/skyradar" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "secret.py" })).not.toBeInTheDocument()
  })

  it("emits selection changes for row and current page checkboxes", async () => {
    const user = userEvent.setup()
    const onToggleSelection = vi.fn()
    const onTogglePageSelection = vi.fn()

    render(
      <MemoryRouter>
        <TooltipProvider>
          <ResultsTable
            results={[leakage]}
            loading={false}
            onMarkIgnored={vi.fn()}
            selectedIds={new Set()}
            onToggleSelection={onToggleSelection}
            onTogglePageSelection={onTogglePageSelection}
          />
        </TooltipProvider>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("checkbox", { name: "选择 acme/skyradar" }))
    await user.click(screen.getByRole("checkbox", { name: "选择本页泄露结果" }))

    expect(onToggleSelection).toHaveBeenCalledWith("leakage-1", true)
    expect(onTogglePageSelection).toHaveBeenCalledWith(true)
  })
})
