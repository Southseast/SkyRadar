import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { OpenAISettings } from "@/features/settings/OpenAISettings"
import { fetchOpenAISetting, saveOpenAISetting } from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  fetchOpenAISetting: vi.fn(),
  saveOpenAISetting: vi.fn(),
}))

const mockedFetchOpenAISetting = vi.mocked(fetchOpenAISetting)
const mockedSaveOpenAISetting = vi.mocked(saveOpenAISetting)

describe("OpenAISettings", () => {
  beforeEach(() => {
    mockedFetchOpenAISetting.mockReset()
    mockedSaveOpenAISetting.mockReset()
  })

  it("loads masked settings and saves configuration without refilling raw api keys", async () => {
    mockedFetchOpenAISetting.mockResolvedValue({
      enabled: false,
      has_api_key: true,
      mask_api_key: "sk-t****alue",
      base_url: "https://api.openai.com/v1",
      model: "gpt-4o-mini",
      prompt: "分析泄露",
      notify_webhook_on_useful: false,
      usefulness_prompt: "判断项目是否值得关注",
      interests: "浏览器指纹与自动化规避",
      max_context_lines: 120,
      max_context_chars: 12000,
      timeout_seconds: 30,
      max_retries: 2,
      concurrency: 2,
    })
    mockedSaveOpenAISetting.mockResolvedValue({
      message: "设置成功",
      data: {
        enabled: true,
        has_api_key: true,
        mask_api_key: "sk-t****alue",
        base_url: "https://api.openai.com/v1",
        model: "gpt-4o-mini",
        prompt: "分析泄露",
        notify_webhook_on_useful: true,
        usefulness_prompt: "判断项目是否值得关注",
        interests: "浏览器指纹与自动化规避",
        max_context_lines: 120,
        max_context_chars: 12000,
        timeout_seconds: 30,
        max_retries: 2,
        concurrency: 2,
      },
    })

    render(<OpenAISettings />)

    expect(await screen.findByLabelText("API Key")).toHaveAttribute("placeholder", "sk-t****alue")
    expect(screen.getByLabelText("API Key")).toHaveValue("")

    await userEvent.click(screen.getByLabelText("启用状态"))
    await userEvent.click(screen.getByLabelText("Webhook Gate"))
    await userEvent.clear(screen.getByLabelText("模型"))
    await userEvent.type(screen.getByLabelText("模型"), "gpt-4.1-mini")
    await userEvent.click(screen.getByRole("button", { name: "保存设置" }))

    await waitFor(() => {
      expect(mockedSaveOpenAISetting).toHaveBeenCalledWith(
        expect.objectContaining({
          enabled: true,
          api_key: "",
          model: "gpt-4.1-mini",
          notify_webhook_on_useful: true,
          usefulness_prompt: "判断项目是否值得关注",
          interests: "浏览器指纹与自动化规避",
          concurrency: 2,
        }),
      )
    })
  })
})
