import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { QueryRules } from "@/features/settings/QueryRules"
import { deleteQueryRule, fetchQueryRules, saveQueryRule } from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  deleteQueryRule: vi.fn(),
  fetchQueryRules: vi.fn(),
  saveQueryRule: vi.fn(),
}))

const mockedFetchQueryRules = vi.mocked(fetchQueryRules)
const mockedSaveQueryRule = vi.mocked(saveQueryRule)
const mockedDeleteQueryRule = vi.mocked(deleteQueryRule)

describe("QueryRules", () => {
  beforeEach(() => {
    mockedFetchQueryRules.mockReset()
    mockedSaveQueryRule.mockReset()
    mockedDeleteQueryRule.mockReset()
  })

  it("loads rules, updates existing rules, toggles enabled, and deletes by tag", async () => {
    mockedFetchQueryRules
      .mockResolvedValueOnce([
        {
          _id: "rule-1",
          tag: "credential",
          keyword: "password OR token",
          enabled: true,
          last: 1_780_000_000,
          api_total: 42,
          found_total: 7,
        },
      ])
      .mockResolvedValueOnce([
        {
          _id: "rule-1",
          tag: "credential",
          keyword: "password OR token",
          enabled: false,
        },
      ])
      .mockResolvedValueOnce([
        {
          _id: "rule-1",
          tag: "credential-renamed",
          keyword: "secret",
          enabled: false,
        },
      ])
    mockedSaveQueryRule.mockResolvedValue({
      message: "更新成功",
    })
    mockedDeleteQueryRule.mockResolvedValue({
      message: "删除成功",
    })

    render(
      <MemoryRouter>
        <QueryRules />
      </MemoryRouter>,
    )

    expect(await screen.findByText("credential")).toBeInTheDocument()
    expect(screen.getByText("password OR token")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("switch", { name: "credential 启用状态" }))

    await waitFor(() => {
      expect(mockedSaveQueryRule).toHaveBeenCalledWith(
        {
          tag: "credential",
          keyword: "password OR token",
          enabled: false,
        },
        "credential",
      )
    })

    await userEvent.click(screen.getByRole("button", { name: "编辑" }))
    await userEvent.clear(screen.getByLabelText("名称"))
    await userEvent.type(screen.getByLabelText("名称"), "credential-renamed")
    await userEvent.clear(screen.getByLabelText("关键字"))
    await userEvent.type(screen.getByLabelText("关键字"), "secret")
    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    await waitFor(() => {
      expect(mockedSaveQueryRule).toHaveBeenLastCalledWith(
        {
          tag: "credential-renamed",
          keyword: "secret",
          enabled: false,
        },
        "credential",
      )
    })

    await userEvent.click(screen.getByRole("button", { name: "删除" }))

    await waitFor(() => {
      expect(mockedDeleteQueryRule).toHaveBeenCalledWith({
        _id: "rule-1",
        tag: "credential-renamed",
        keyword: "secret",
        enabled: false,
      })
    })
    expect(await screen.findByText("暂无查询规则")).toBeInTheDocument()
  })

  it("creates new rules without an existing tag", async () => {
    mockedFetchQueryRules.mockResolvedValueOnce([]).mockResolvedValueOnce([
      {
        _id: "rule-2",
        tag: "secret",
        keyword: "api_key",
        enabled: true,
      },
    ])
    mockedSaveQueryRule.mockResolvedValue({
      message: "保存成功",
    })

    render(
      <MemoryRouter>
        <QueryRules />
      </MemoryRouter>,
    )

    expect(await screen.findByText("暂无查询规则")).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText("名称"), "secret")
    await userEvent.type(screen.getByLabelText("关键字"), "api_key")
    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    await waitFor(() => {
      expect(mockedSaveQueryRule).toHaveBeenCalledWith(
        {
          tag: "secret",
          keyword: "api_key",
          enabled: true,
        },
        undefined,
      )
    })
  })
})
