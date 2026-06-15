import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { NoticeSettings } from "@/features/settings/NoticeSettings"
import {
  addNoticeMail,
  deleteNoticeMail,
  deleteWebhookSetting,
  fetchNoticeMails,
  fetchSmtpSetting,
  fetchWebhookSettings,
  saveSmtpSetting,
  saveWebhookSetting,
  testWebhookSetting,
} from "@/lib/api/settings"

vi.mock("@/lib/api/settings", () => ({
  addNoticeMail: vi.fn(),
  deleteNoticeMail: vi.fn(),
  deleteWebhookSetting: vi.fn(),
  fetchNoticeMails: vi.fn(),
  fetchSmtpSetting: vi.fn(),
  fetchWebhookSettings: vi.fn(),
  saveSmtpSetting: vi.fn(),
  saveWebhookSetting: vi.fn(),
  testWebhookSetting: vi.fn(),
}))

const mockedFetchNoticeMails = vi.mocked(fetchNoticeMails)
const mockedFetchSmtpSetting = vi.mocked(fetchSmtpSetting)
const mockedFetchWebhookSettings = vi.mocked(fetchWebhookSettings)
const mockedAddNoticeMail = vi.mocked(addNoticeMail)
const mockedDeleteNoticeMail = vi.mocked(deleteNoticeMail)
const mockedSaveSmtpSetting = vi.mocked(saveSmtpSetting)
const mockedSaveWebhookSetting = vi.mocked(saveWebhookSetting)
const mockedTestWebhookSetting = vi.mocked(testWebhookSetting)
const mockedDeleteWebhookSetting = vi.mocked(deleteWebhookSetting)

describe("NoticeSettings", () => {
  beforeEach(() => {
    mockedFetchNoticeMails.mockReset()
    mockedFetchSmtpSetting.mockReset()
    mockedFetchWebhookSettings.mockReset()
    mockedAddNoticeMail.mockReset()
    mockedDeleteNoticeMail.mockReset()
    mockedSaveSmtpSetting.mockReset()
    mockedSaveWebhookSetting.mockReset()
    mockedTestWebhookSetting.mockReset()
    mockedDeleteWebhookSetting.mockReset()
  })

  it("manages mails, SMTP, and Webhook settings with compatible payloads", async () => {
    mockedFetchNoticeMails.mockResolvedValueOnce([{ mail: "sec@example.com" }]).mockResolvedValueOnce([{ mail: "ops@example.com" }])
    mockedFetchSmtpSetting.mockResolvedValue({ host: "smtp.example.com", port: 25, enabled: true })
    mockedFetchWebhookSettings.mockResolvedValueOnce([
      { provider: "dingtalk", webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=abc", enabled: true, has_secret: true },
    ])
    mockedFetchWebhookSettings.mockResolvedValueOnce([
      {
        provider: "dingtalk",
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=***",
        webhook_id: "next-webhook-id",
        enabled: true,
        has_secret: true,
      },
    ])
    mockedAddNoticeMail.mockResolvedValue({ message: "添加成功" })
    mockedDeleteNoticeMail.mockResolvedValue({ message: "删除成功" })
    mockedSaveSmtpSetting.mockResolvedValue({ message: "设置成功", data: { host: "smtp.next.com", port: 465, enabled: true } })
    mockedSaveWebhookSetting.mockResolvedValue({ message: "设置成功" })
    mockedTestWebhookSetting.mockResolvedValue({ message: "已发送，请前往目标群查看" })
    mockedDeleteWebhookSetting.mockResolvedValue({ message: "删除成功" })

    render(<NoticeSettings />)

    expect(await screen.findByText("sec@example.com")).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText("邮箱"))
    await userEvent.type(screen.getByLabelText("邮箱"), "ops@example.com")
    await userEvent.click(screen.getByRole("button", { name: "添加" }))

    await waitFor(() => {
      expect(mockedAddNoticeMail).toHaveBeenCalledWith("ops@example.com")
    })

    await userEvent.click(screen.getAllByRole("button", { name: "删除" })[0])

    await waitFor(() => {
      expect(mockedDeleteNoticeMail).toHaveBeenCalledWith("ops@example.com")
    })

    await userEvent.clear(screen.getByLabelText("服务器地址"))
    await userEvent.type(screen.getByLabelText("服务器地址"), "smtp.next.com")
    await userEvent.clear(screen.getByLabelText("服务器端口"))
    await userEvent.type(screen.getByLabelText("服务器端口"), "465")
    const tlsSwitch = screen.getByRole("switch", { name: "TLS 加密" })
    const smtpEnabledSwitch = screen.getAllByRole("switch", { name: "开启通知" })[0]

    expect(tlsSwitch).toHaveAttribute("type", "button")
    expect(smtpEnabledSwitch).toHaveAttribute("type", "button")

    await userEvent.click(tlsSwitch)
    await userEvent.click(smtpEnabledSwitch)

    expect(tlsSwitch).toHaveAttribute("data-state", "checked")
    expect(smtpEnabledSwitch).toHaveAttribute("data-state", "unchecked")

    expect(mockedSaveSmtpSetting).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole("button", { name: "保存 SMTP" }))

    await waitFor(() => {
      expect(mockedSaveSmtpSetting).toHaveBeenCalledWith(expect.objectContaining({ host: "smtp.next.com", port: 465, tls: true, enabled: false }))
    })

    await userEvent.type(screen.getByLabelText("Webhook 地址"), "https://oapi.dingtalk.com/robot/send?access_token=next")
    await userEvent.type(screen.getByLabelText("加签 Secret"), "ding-secret")
    const webhookEnabledSwitch = screen.getAllByRole("switch", { name: "开启通知" })[1]

    expect(webhookEnabledSwitch).toHaveAttribute("type", "button")

    await userEvent.click(webhookEnabledSwitch)

    expect(webhookEnabledSwitch).toHaveAttribute("data-state", "unchecked")

    expect(mockedTestWebhookSetting).not.toHaveBeenCalled()
    expect(mockedSaveWebhookSetting).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole("button", { name: "测试" }))

    await waitFor(() => {
      expect(mockedTestWebhookSetting).toHaveBeenCalledWith(
        expect.objectContaining({
          webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=next",
          provider: "dingtalk",
          secret: "ding-secret",
          enabled: false,
        })
      )
    })

    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    await waitFor(() => {
      expect(mockedSaveWebhookSetting).toHaveBeenCalledWith(
        expect.objectContaining({
          webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=next",
          provider: "dingtalk",
          secret: "ding-secret",
          enabled: false,
        })
      )
    })

    await userEvent.click(screen.getByRole("button", { name: "删除" }))

    await waitFor(() => {
      expect(mockedDeleteWebhookSetting).toHaveBeenCalledWith(
        expect.objectContaining({
          webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=***",
          webhook_id: "next-webhook-id",
        })
      )
    })
  })

  it("requires secret for webhook before testing or saving", async () => {
    mockedFetchNoticeMails.mockResolvedValue([])
    mockedFetchSmtpSetting.mockResolvedValue(null)
    mockedFetchWebhookSettings.mockResolvedValue([])

    render(<NoticeSettings />)

    await screen.findByText("暂无邮件接收人。")

    await userEvent.type(screen.getByLabelText("Webhook 地址"), "https://oapi.dingtalk.com/robot/send?access_token=abc")
    await userEvent.click(screen.getByRole("button", { name: "测试" }))

    expect(await screen.findByText("webhook 必须配置加签 Secret。")).toBeInTheDocument()
    expect(mockedTestWebhookSetting).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    expect(mockedSaveWebhookSetting).not.toHaveBeenCalled()
  })

  it("rejects provider mismatched URL before testing or saving", async () => {
    mockedFetchNoticeMails.mockResolvedValue([])
    mockedFetchSmtpSetting.mockResolvedValue(null)
    mockedFetchWebhookSettings.mockResolvedValue([])

    render(<NoticeSettings />)

    await screen.findByText("暂无邮件接收人。")

    await userEvent.type(screen.getByLabelText("Webhook 地址"), "https://example.com/robot/send")
    await userEvent.type(screen.getByLabelText("加签 Secret"), "ding-secret")
    await userEvent.click(screen.getByRole("button", { name: "测试" }))

    expect(await screen.findByText("webhook 地址和类型不匹配。")).toBeInTheDocument()
    expect(mockedTestWebhookSetting).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    expect(mockedSaveWebhookSetting).not.toHaveBeenCalled()
  })
})
