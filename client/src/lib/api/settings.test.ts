import type { AxiosResponse } from "axios"
import { afterEach, describe, expect, it, vi } from "vitest"

import { apiClient } from "@/lib/api/client"
import {
  addGithubAccount,
  deleteGithubAccount,
  deleteQueryRule,
  deleteWebhookSetting,
  fetchBlacklist,
  fetchGithubAccounts,
  fetchNoticeMails,
  fetchQueryRules,
  fetchWebhookSettings,
  saveQueryRule,
  saveSmtpSetting,
} from "@/lib/api/settings"

describe("settings api adapter", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("removes raw GitHub passwords from fetched accounts", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        data: [
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
        data: [{ username: "smoke-user", password: "raw-token", mask_password: "ra****en" }],
      },
    } as AxiosResponse)
    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValue({
      status: 204,
      data: undefined,
    } as AxiosResponse)

    const added = await addGithubAccount({ username: "smoke-user", password: "raw-token" })
    const deleted = await deleteGithubAccount("smoke-user")

    expect(added.data).toEqual([{ username: "smoke-user", mask_password: "ra****en" }])
    expect(deleted.data).toEqual([])
    expect(deleted.message).toBe("删除成功")
    expect(deleteSpy).toHaveBeenCalledWith("/api/v1/github-accounts/smoke-user")
    expect(JSON.stringify({ added, deleted })).not.toContain("raw-token")
    expect(JSON.stringify({ added, deleted })).not.toContain("other-token")
  })

  it("omits an empty SMTP password from save payloads", async () => {
    const putSpy = vi.spyOn(apiClient, "put").mockResolvedValue({
      data: { data: null },
    } as AxiosResponse)

    await saveSmtpSetting({
      host: "smtp.example.com",
      port: 465,
      username: "notice",
      password: "",
      enabled: true,
    })

    expect(putSpy).toHaveBeenCalledWith(
      "/api/v1/mail-settings/current",
      expect.not.objectContaining({
        password: "",
      })
    )
  })

  it("deletes search rules by tag path", async () => {
    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValue({
      status: 204,
      data: undefined,
    } as AxiosResponse)

    await deleteQueryRule({
      tag: "credential/token",
    })

    expect(deleteSpy).toHaveBeenCalledWith("/api/v1/search-rules/credential%2Ftoken")
  })

  it("creates search rules with the collection endpoint", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValue({
      data: { data: [] },
    } as AxiosResponse)

    await saveQueryRule({
      tag: "credential",
      keyword: "password OR token",
      enabled: true,
    })

    expect(postSpy).toHaveBeenCalledWith("/api/v1/search-rules", {
      tag: "credential",
      keyword: "password OR token",
      enabled: true,
    })
  })

  it("updates search rules by tag path", async () => {
    const putSpy = vi.spyOn(apiClient, "put").mockResolvedValue({
      data: { data: [] },
    } as AxiosResponse)

    await saveQueryRule(
      {
        tag: "credential-renamed",
        keyword: "secret",
        enabled: false,
      },
      "credential/token",
    )

    expect(putSpy).toHaveBeenCalledWith("/api/v1/search-rules/credential%2Ftoken", {
      tag: "credential-renamed",
      keyword: "secret",
      enabled: false,
    })
  })

  it("deletes Webhook settings by webhook_id when available", async () => {
    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValue({
      status: 204,
      data: undefined,
    } as AxiosResponse)

    await deleteWebhookSetting({
      webhook_id: "hashed-webhook",
    })

    expect(deleteSpy).toHaveBeenCalledWith(expect.stringContaining("/api/v1/webhooks/hashed-webhook"))
  })

  it("normalizes malformed list results", async () => {
    const getSpy = vi
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: { data: null } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { data: { username: "octo" } } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { data: null } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { data: { text: "secret" } } } as AxiosResponse)
      .mockResolvedValueOnce({ data: { data: null } } as AxiosResponse)

    await expect(fetchNoticeMails()).resolves.toEqual([])
    await expect(fetchGithubAccounts()).resolves.toEqual([])
    await expect(fetchQueryRules()).resolves.toEqual([])
    await expect(fetchBlacklist()).resolves.toEqual([])
    await expect(fetchWebhookSettings()).resolves.toEqual([])

    expect(getSpy).toHaveBeenCalledTimes(5)
  })
})
