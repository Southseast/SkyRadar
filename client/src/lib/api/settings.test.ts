import type { AxiosResponse } from "axios"
import { afterEach, describe, expect, it, vi } from "vitest"

import { apiClient } from "@/lib/api/client"
import {
  addGithubAccount,
  deleteGithubAccount,
  deleteWebhookSetting,
  fetchBlacklist,
  fetchGithubAccounts,
  fetchNoticeMails,
  fetchQueryRules,
  fetchWebhookSettings,
  saveSmtpSetting,
} from "@/lib/api/settings"

describe("settings api adapter", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("removes raw GitHub passwords from fetched accounts", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        result: [
          {
            username: "smoke-user",
            password: "raw-token",
            mask_password: "ra****en",
            rate_limit: 1000,
            rate_remaining: 999,
          },
        ],
      },
    } as AxiosResponse)

    const accounts = await fetchGithubAccounts()

    expect(accounts).toEqual([
      {
        username: "smoke-user",
        mask_password: "ra****en",
        rate_limit: 1000,
        rate_remaining: 999,
      },
    ])
    expect(JSON.stringify(accounts)).not.toContain("raw-token")
  })

  it("removes raw GitHub passwords from add and delete responses", async () => {
    vi.spyOn(apiClient, "post").mockResolvedValue({
      data: {
        status: 201,
        msg: "添加成功",
        result: [{ username: "smoke-user", password: "raw-token", mask_password: "ra****en" }],
      },
    } as AxiosResponse)
    vi.spyOn(apiClient, "delete").mockResolvedValue({
      data: {
        status: 404,
        msg: "删除成功",
        result: [{ username: "smoke-user", password: "other-token", mask_password: "ot****en" }],
      },
    } as AxiosResponse)

    const added = await addGithubAccount({ username: "smoke-user", password: "raw-token" })
    const deleted = await deleteGithubAccount("smoke-user")

    expect(added.result).toEqual([{ username: "smoke-user", mask_password: "ra****en" }])
    expect(deleted.result).toEqual([{ username: "smoke-user", mask_password: "ot****en" }])
    expect(JSON.stringify({ added, deleted })).not.toContain("raw-token")
    expect(JSON.stringify({ added, deleted })).not.toContain("other-token")
  })

  it("omits an empty SMTP password from save payloads", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValue({
      data: { status: 201, msg: "设置成功", result: null },
    } as AxiosResponse)

    await saveSmtpSetting({
      host: "smtp.example.com",
      port: 465,
      username: "notice",
      password: "",
      enabled: true,
    })

    expect(postSpy).toHaveBeenCalledWith(
      expect.any(String),
      expect.not.objectContaining({
        password: "",
      })
    )
  })

  it("deletes Webhook settings by webhook_hash when available", async () => {
    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValue({
      data: { status: 200, msg: "删除成功", result: [] },
    } as AxiosResponse)

    await deleteWebhookSetting({
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=***",
      webhook_hash: "hashed-webhook",
    })

    expect(deleteSpy).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        params: { webhook_hash: "hashed-webhook" },
      })
    )
  })

  it("normalizes malformed list results", async () => {
    const getSpy = vi
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: { result: null } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { result: { username: "octo" } } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { result: null } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { result: { text: "secret" } } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { result: null } } as AxiosResponse)

    await expect(fetchNoticeMails()).resolves.toEqual([])
    await expect(fetchGithubAccounts()).resolves.toEqual([])
    await expect(fetchQueryRules()).resolves.toEqual([])
    await expect(fetchBlacklist()).resolves.toEqual([])
    await expect(fetchWebhookSettings()).resolves.toEqual([])

    expect(getSpy).toHaveBeenCalledTimes(5)
  })
})
