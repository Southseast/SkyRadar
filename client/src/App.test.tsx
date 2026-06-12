import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"
import App from "./App"

describe("App", () => {
  it("renders the SkyRadar workbench shell", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <TooltipProvider>
          <App />
        </TooltipProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText("SkyRadar")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "项目发现" })).toBeInTheDocument()
  })
})
