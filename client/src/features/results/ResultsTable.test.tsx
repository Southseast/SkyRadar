import { render, screen } from "@testing-library/react"
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
  datetime: "2026-06-05T08:00:00Z",
}

describe("ResultsTable", () => {
  it("renders separate actions for leakage detail code and GitHub source", () => {
    render(
      <MemoryRouter>
        <TooltipProvider>
          <ResultsTable results={[leakage]} loading={false} onMarkIgnored={vi.fn()} />
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
          <ResultsTable results={[leakage]} loading={false} onMarkIgnored={vi.fn()} />
        </TooltipProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText("仓库")).toBeInTheDocument()
    expect(screen.getByText("文件")).toBeInTheDocument()
    expect(screen.getByText("acme/skyradar")).toBeInTheDocument()
    expect(screen.getByText("secret.py")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "acme/skyradar" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "secret.py" })).not.toBeInTheDocument()
  })
})
