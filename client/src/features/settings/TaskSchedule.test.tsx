import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { TaskSchedule } from "@/features/settings/TaskSchedule"
import { fetchTaskSetting, saveTaskSetting } from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  fetchTaskSetting: vi.fn(),
  saveTaskSetting: vi.fn(),
}))

const mockedFetchTaskSetting = vi.mocked(fetchTaskSetting)
const mockedSaveTaskSetting = vi.mocked(saveTaskSetting)

describe("TaskSchedule", () => {
  beforeEach(() => {
    mockedFetchTaskSetting.mockReset()
    mockedSaveTaskSetting.mockReset()
  })

  it("uses defaults for missing setting and saves compatible payload", async () => {
    mockedFetchTaskSetting.mockResolvedValue({ status: 400, msg: "请配置查询页数和周期", result: null })
    mockedSaveTaskSetting.mockResolvedValue({ status: 201, msg: "设置成功", result: [] })

    render(<TaskSchedule />)

    expect(await screen.findByText("请配置查询页数和周期")).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText("时间间隔（分钟）"))
    await userEvent.type(screen.getByLabelText("时间间隔（分钟）"), "15")
    await userEvent.clear(screen.getByLabelText("页数（30条/页）"))
    await userEvent.type(screen.getByLabelText("页数（30条/页）"), "3")
    await userEvent.click(screen.getByRole("button", { name: "确认" }))

    await waitFor(() => {
      expect(mockedSaveTaskSetting).toHaveBeenCalledWith({
        minute: 15,
        page: 3,
      })
    })
    expect(screen.getByText("设置成功")).toBeInTheDocument()
  })
})
