import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { GithubAccounts } from "@/features/settings/GithubAccounts"
import { addGithubAccount, deleteGithubAccount, fetchGithubAccounts } from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  addGithubAccount: vi.fn(),
  deleteGithubAccount: vi.fn(),
  fetchGithubAccounts: vi.fn(),
}))

const mockedFetchGithubAccounts = vi.mocked(fetchGithubAccounts)
const mockedAddGithubAccount = vi.mocked(addGithubAccount)
const mockedDeleteGithubAccount = vi.mocked(deleteGithubAccount)

describe("GithubAccounts", () => {
  beforeEach(() => {
    mockedFetchGithubAccounts.mockReset()
    mockedAddGithubAccount.mockReset()
    mockedDeleteGithubAccount.mockReset()
  })

  it("loads accounts, adds an account, and deletes by username", async () => {
    mockedFetchGithubAccounts.mockResolvedValue([
      {
        username: "octo",
        mask_password: "to****en",
        rate_limit: 30,
        rate_remaining: 15,
      },
    ])
    mockedAddGithubAccount.mockResolvedValue({
      status: 201,
      msg: "添加成功",
      result: [
        {
          username: "next",
          mask_password: "ne****en",
          rate_limit: 30,
          rate_remaining: 30,
        },
      ],
    })
    mockedDeleteGithubAccount.mockResolvedValue({
      status: 404,
      msg: "删除成功",
      result: [],
    })

    render(<GithubAccounts />)

    expect(await screen.findByText("octo")).toBeInTheDocument()
    expect(screen.getByText("剩余 15")).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText("账号"), "next")
    await userEvent.type(screen.getByLabelText("密码或 token"), "next-token")
    await userEvent.click(screen.getByRole("button", { name: "添加" }))

    await waitFor(() => {
      expect(mockedAddGithubAccount).toHaveBeenCalledWith({
        username: "next",
        password: "next-token",
      })
    })
    expect(await screen.findByText("next")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "删除" }))

    await waitFor(() => {
      expect(mockedDeleteGithubAccount).toHaveBeenCalledWith("next")
    })
    expect(await screen.findByText("暂无 GitHub 账号")).toBeInTheDocument()
  })
})
