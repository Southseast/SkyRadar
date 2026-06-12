import { apiClient } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type {
  ApiResponse,
  BlacklistItem,
  GithubAccount,
  NoticeMail,
  QueryRule,
  SmtpSetting,
  TaskSetting,
  WebhookSetting,
} from "@/types/api"

export interface GithubAccountPayload {
  username: string
  password: string
}

export async function fetchGithubAccounts() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.settingGithub)
  return sanitizeGithubAccounts(response.data.result)
}

export async function addGithubAccount(payload: GithubAccountPayload) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingGithub, payload)
  return {
    ...response.data,
    result: sanitizeGithubAccounts(response.data.result),
  }
}

export async function deleteGithubAccount(username: string) {
  const response = await apiClient.delete<ApiResponse<unknown>>(endpoints.settingGithub, {
    params: { username },
  })
  return {
    ...response.data,
    result: sanitizeGithubAccounts(response.data.result),
  }
}

function sanitizeGithubAccounts(accounts: unknown): GithubAccount[] {
  return normalizeList<GithubAccount>(accounts).map((account) => {
    const safeAccount = { ...account } as GithubAccount & { password?: unknown }
    delete safeAccount.password
    return safeAccount
  })
}

export interface QueryRulePayload {
  tag: string
  keyword: string
  enabled: boolean
}

export async function fetchQueryRules() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.settingQuery)
  return normalizeList<QueryRule>(response.data.result)
}

export async function saveQueryRule(payload: QueryRulePayload) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingQuery, payload)
  return {
    ...response.data,
    result: normalizeList<QueryRule>(response.data.result),
  }
}

export async function deleteQueryRule(rule: Pick<QueryRule, "_id" | "tag">) {
  const response = await apiClient.delete<ApiResponse<unknown>>(endpoints.settingQuery, {
    params: {
      _id: rule._id,
      tag: rule.tag,
    },
  })
  return {
    ...response.data,
    result: normalizeList<QueryRule>(response.data.result),
  }
}

export interface TaskSettingPayload {
  page: number
  minute: number
}

export async function fetchTaskSetting() {
  const response = await apiClient.get<ApiResponse<TaskSetting | null>>(endpoints.settingCron)
  return response.data
}

export async function saveTaskSetting(payload: TaskSettingPayload) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingCron, payload)
  return response.data
}

export async function fetchBlacklist() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.settingBlacklist)
  return normalizeList<BlacklistItem>(response.data.result)
}

export async function addBlacklistItem(text: string) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingBlacklist, { text })
  return {
    ...response.data,
    result: normalizeList<BlacklistItem>(response.data.result),
  }
}

export async function deleteBlacklistItem(text: string) {
  const response = await apiClient.delete<ApiResponse<unknown>>(endpoints.settingBlacklist, {
    params: { text },
  })
  return {
    ...response.data,
    result: normalizeList<BlacklistItem>(response.data.result),
  }
}

export async function fetchNoticeMails() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.settingNotice)
  return normalizeList<NoticeMail>(response.data.result)
}

export async function addNoticeMail(mail: string) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingNotice, { mail })
  return {
    ...response.data,
    result: normalizeList<NoticeMail>(response.data.result),
  }
}

export async function deleteNoticeMail(mail: string) {
  const response = await apiClient.delete<ApiResponse<unknown>>(endpoints.settingNotice, {
    params: { mail },
  })
  return {
    ...response.data,
    result: normalizeList<NoticeMail>(response.data.result),
  }
}

export async function fetchSmtpSetting() {
  const response = await apiClient.get<ApiResponse<SmtpSetting | null>>(endpoints.settingMail)
  return response.data.result
}

export async function saveSmtpSetting(payload: SmtpSetting) {
  const safePayload = { ...payload }
  if (safePayload.password === "") delete safePayload.password

  const response = await apiClient.post<ApiResponse<SmtpSetting | null>>(endpoints.settingMail, safePayload)
  return response.data
}

export async function fetchWebhookSettings() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.settingWebhook)
  return normalizeList<WebhookSetting>(response.data.result)
}

export async function saveWebhookSetting(payload: WebhookSetting) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingWebhook, payload)
  return response.data
}

export async function testWebhookSetting(payload: WebhookSetting) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.settingWebhook, { ...payload, test: true })
  return response.data
}

export async function deleteWebhookSetting(webhook: string | Pick<WebhookSetting, "webhook_url" | "webhook_hash">) {
  const params =
    typeof webhook === "string"
      ? { webhook_url: webhook }
      : webhook.webhook_hash
        ? { webhook_hash: webhook.webhook_hash }
        : { webhook_url: webhook.webhook_url }
  const response = await apiClient.delete<ApiResponse<unknown>>(endpoints.settingWebhook, {
    params,
  })
  return response.data
}

function normalizeList<T>(result: unknown): T[] {
  return Array.isArray(result) ? result : []
}
