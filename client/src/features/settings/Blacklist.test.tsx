import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Blacklist } from "@/features/settings/Blacklist"
import { addBlacklistItem, deleteBlacklistItem, fetchBlacklist } from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  addBlacklistItem: vi.fn(),
  deleteBlacklistItem: vi.fn(),
  fetchBlacklist: vi.fn(),
}))

const mockedFetchBlacklist = vi.mocked(fetchBlacklist)
const mockedAddBlacklistItem = vi.mocked(addBlacklistItem)
const mockedDeleteBlacklistItem = vi.mocked(deleteBlacklistItem)

describe("Blacklist", () => {
  beforeEach(() => {
    mockedFetchBlacklist.mockReset()
    mockedAddBlacklistItem.mockReset()
    mockedDeleteBlacklistItem.mockReset()
  })

  it("loads, adds, and deletes blacklist items with text payload", async () => {
    mockedFetchBlacklist.mockResolvedValueOnce([{ text: "demo" }]).mockResolvedValueOnce([{ text: "secret" }])
    mockedAddBlacklistItem.mockResolvedValue({
      message: "添加成功",
    })
    mockedDeleteBlacklistItem.mockResolvedValue({
      message: "删除成功",
    })

    render(<Blacklist />)

    expect(await screen.findByText("demo")).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText("关键字"), " secret ")
    await userEvent.click(screen.getByRole("button", { name: "添加" }))

    await waitFor(() => {
      expect(mockedAddBlacklistItem).toHaveBeenCalledWith("secret")
    })
    expect(await screen.findByText("secret")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "删除" }))

    await waitFor(() => {
      expect(mockedDeleteBlacklistItem).toHaveBeenCalledWith("secret")
    })
    expect(await screen.findByText("暂无黑名单关键字")).toBeInTheDocument()
  })
})
