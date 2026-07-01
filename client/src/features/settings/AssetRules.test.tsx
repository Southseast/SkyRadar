import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { AssetRules } from "@/features/settings/AssetRules"
import { deleteAssetRule, fetchAssetRules, saveAssetRule } from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  deleteAssetRule: vi.fn(),
  fetchAssetRules: vi.fn(),
  saveAssetRule: vi.fn(),
}))

const mockedFetchAssetRules = vi.mocked(fetchAssetRules)
const mockedSaveAssetRule = vi.mocked(saveAssetRule)
const mockedDeleteAssetRule = vi.mocked(deleteAssetRule)

describe("AssetRules", () => {
  beforeEach(() => {
    mockedFetchAssetRules.mockReset()
    mockedSaveAssetRule.mockReset()
    mockedDeleteAssetRule.mockReset()
  })

  it("loads preset rules, creates custom rules, toggles rules, and deletes rules", async () => {
    mockedFetchAssetRules
      .mockResolvedValueOnce([
        {
          _id: "email",
          name: "Email",
          type: "email",
          pattern: "@",
          enabled: true,
          builtin: true,
        },
        {
          _id: "aws",
          name: "AWS Key",
          type: "secret",
          pattern: "AKIA[0-9A-Z]{16}",
          enabled: true,
          builtin: false,
        },
      ])
      .mockResolvedValueOnce([
        {
          _id: "custom",
          name: "Custom Token",
          type: "secret",
          pattern: "token_[a-z]+",
          enabled: true,
          builtin: false,
        },
      ])
      .mockResolvedValueOnce([
        {
          _id: "custom",
          name: "Custom Token",
          type: "secret",
          pattern: "token_[a-z]+",
          enabled: false,
          builtin: false,
        },
      ])
    mockedSaveAssetRule.mockResolvedValue({ message: "保存成功" })
    mockedDeleteAssetRule.mockResolvedValue({ message: "删除成功" })

    render(<AssetRules />)

    expect(await screen.findByText("Email")).toBeInTheDocument()
    expect(screen.getByText("预置")).toBeInTheDocument()
    expect(screen.getByText("AWS Key")).toBeInTheDocument()

    const initialDeleteButtons = screen.getAllByRole("button", { name: "删除" })
    expect(initialDeleteButtons[0]).toBeEnabled()
    await userEvent.click(initialDeleteButtons[0])

    await waitFor(() => {
      expect(mockedDeleteAssetRule).toHaveBeenCalledWith({
        _id: "email",
        name: "Email",
        type: "email",
        pattern: "@",
        enabled: true,
        builtin: true,
      })
    })

    await userEvent.type(screen.getByLabelText("名称"), "Custom Token")
    await userEvent.type(screen.getByLabelText("类型"), "secret")
    fireEvent.change(screen.getByLabelText("正则表达式"), { target: { value: "token_[a-z]+" } })
    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    await waitFor(() => {
      expect(mockedSaveAssetRule).toHaveBeenCalledWith(
        {
          name: "Custom Token",
          type: "secret",
          pattern: "token_[a-z]+",
          enabled: true,
        },
        undefined,
      )
    })

    await userEvent.click(screen.getByRole("switch", { name: "Custom Token 启用状态" }))

    await waitFor(() => {
      expect(mockedSaveAssetRule).toHaveBeenLastCalledWith(
        {
          name: "Custom Token",
          type: "secret",
          pattern: "token_[a-z]+",
          enabled: false,
        },
        "custom",
      )
    })

    const deleteButtons = screen.getAllByRole("button", { name: "删除" })
    await userEvent.click(deleteButtons[deleteButtons.length - 1])

    await waitFor(() => {
      expect(mockedDeleteAssetRule).toHaveBeenLastCalledWith({
        _id: "custom",
        name: "Custom Token",
        type: "secret",
        pattern: "token_[a-z]+",
        enabled: false,
        builtin: false,
      })
    })
  })
})
