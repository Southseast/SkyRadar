import { apiClient, getResponseData, toMutationResult } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type {
  ApiResponse,
  AssetRule,
  BlacklistItem,
  GithubAccount,
  NoticeMail,
  OpenAISetting,
  OpenAISettingPayload,
  QueryRule,
  QueryRuleSearchType,
  SmtpSetting,
  TaskSetting,
  WebhookSetting,
} from "@/types/api"

export interface GithubAccountPayload {
  username: string
  password: string
}

export async function fetchGithubAccounts() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.githubAccounts)
  return sanitizeGithubAccounts(getResponseData(response.data))
}

export async function addGithubAccount(payload: GithubAccountPayload) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.githubAccounts, payload)
  return toMutationResult(sanitizeGithubAccounts(getResponseData(response.data)), "添加成功")
}

export async function deleteGithubAccount(username: string) {
  const response = await apiClient.delete<ApiResponse<unknown> | undefined>(endpoints.githubAccount(username))
  return toMutationResult(sanitizeGithubAccounts(getResponseData(response.data)), "删除成功")
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
  search_type: QueryRuleSearchType
  enabled: boolean
  analysis_enabled: boolean
}

export async function fetchQueryRules() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.searchRules)
  return normalizeQueryRules(getResponseData(response.data))
}

export async function fetchOpenAISetting() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.openAISettingsCurrent)
  return sanitizeOpenAISetting(getResponseData(response.data))
}

export async function saveOpenAISetting(payload: OpenAISettingPayload) {
  const safePayload = { ...payload }
  if (safePayload.api_key === "") delete safePayload.api_key

  const response = await apiClient.put<ApiResponse<unknown>>(endpoints.openAISettingsCurrent, safePayload)
  return toMutationResult(sanitizeOpenAISetting(getResponseData(response.data)) ?? undefined, "设置成功")
}

export async function saveQueryRule(payload: QueryRulePayload, existingTag?: string) {
  const response = existingTag
    ? await apiClient.put<ApiResponse<unknown>>(endpoints.searchRule(existingTag), payload)
    : await apiClient.post<ApiResponse<unknown>>(endpoints.searchRules, payload)
  return toMutationResult(normalizeQueryRules(getResponseData(response.data)), "保存成功")
}

export async function deleteQueryRule(rule: Pick<QueryRule, "tag">) {
  const response = await apiClient.delete<ApiResponse<unknown> | undefined>(endpoints.searchRule(rule.tag))
  return toMutationResult(normalizeList<QueryRule>(getResponseData(response.data)), "删除成功")
}

export interface TaskSettingPayload {
  page: number
  minute: number
}

export async function fetchTaskSetting() {
  const response = await apiClient.get<ApiResponse<TaskSetting | null>>(endpoints.taskScheduleCurrent)
  const result = getResponseData(response.data)
  return toMutationResult(result ?? undefined, result ? "设置已加载" : "请配置查询页数和周期")
}

export async function saveTaskSetting(payload: TaskSettingPayload) {
  const response = await apiClient.put<ApiResponse<unknown>>(endpoints.taskScheduleCurrent, payload)
  return toMutationResult(getResponseData(response.data), "设置成功")
}

export async function fetchBlacklist() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.blacklistItems)
  return normalizeList<BlacklistItem>(getResponseData(response.data))
}

export async function addBlacklistItem(text: string) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.blacklistItems, { text })
  return toMutationResult(normalizeList<BlacklistItem>(getResponseData(response.data)), "添加成功")
}

export async function deleteBlacklistItem(text: string) {
  const response = await apiClient.delete<ApiResponse<unknown> | undefined>(endpoints.blacklistItem(text))
  return toMutationResult(normalizeList<BlacklistItem>(getResponseData(response.data)), "删除成功")
}

export type AssetRulePayload = Pick<AssetRule, "name" | "type" | "pattern" | "enabled">

export async function fetchAssetRules() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.assetRules)
  return normalizeList<AssetRule>(getResponseData(response.data))
}

export async function saveAssetRule(payload: AssetRulePayload, existingId?: string) {
  const response = existingId
    ? await apiClient.put<ApiResponse<unknown>>(endpoints.assetRule(existingId), payload)
    : await apiClient.post<ApiResponse<unknown>>(endpoints.assetRules, payload)
  return toMutationResult(getResponseData(response.data), "保存成功")
}

export async function deleteAssetRule(rule: Pick<AssetRule, "_id">) {
  const response = await apiClient.delete<ApiResponse<unknown> | undefined>(endpoints.assetRule(rule._id))
  return toMutationResult(getResponseData(response.data), "删除成功")
}

export async function fetchNoticeMails() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.notificationRecipients)
  return normalizeList<NoticeMail>(getResponseData(response.data))
}

export async function addNoticeMail(mail: string) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.notificationRecipients, { mail })
  return toMutationResult(normalizeList<NoticeMail>(getResponseData(response.data)), "添加成功")
}

export async function deleteNoticeMail(mail: string) {
  const response = await apiClient.delete<ApiResponse<unknown> | undefined>(endpoints.notificationRecipient(mail))
  return toMutationResult(normalizeList<NoticeMail>(getResponseData(response.data)), "删除成功")
}

export async function fetchSmtpSetting() {
  const response = await apiClient.get<ApiResponse<SmtpSetting | null>>(endpoints.mailSettingsCurrent)
  return sanitizeSmtpSetting(getResponseData(response.data))
}

export async function saveSmtpSetting(payload: SmtpSetting) {
  const safePayload = { ...payload }
  if (safePayload.password === "") delete safePayload.password

  const response = await apiClient.put<ApiResponse<SmtpSetting | null>>(endpoints.mailSettingsCurrent, safePayload)
  return toMutationResult(sanitizeSmtpSetting(getResponseData(response.data)) ?? undefined, "设置成功")
}

export async function fetchWebhookSettings() {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.webhooks)
  return sanitizeWebhookSettings(getResponseData(response.data))
}

export async function saveWebhookSetting(payload: WebhookSetting) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.webhooks, payload)
  return toMutationResult(getResponseData(response.data), "设置成功")
}

export async function testWebhookSetting(payload: WebhookSetting) {
  const response = await apiClient.post<ApiResponse<unknown>>(endpoints.webhookTests, payload)
  return toMutationResult(getResponseData(response.data), "测试消息已发送")
}

export async function deleteWebhookSetting(webhook: Pick<WebhookSetting, "webhook_id">) {
  if (!webhook.webhook_id) {
    throw new Error("webhook_id is required")
  }
  const response = await apiClient.delete<ApiResponse<unknown> | undefined>(endpoints.webhook(webhook.webhook_id))
  return toMutationResult(getResponseData(response.data), "删除成功")
}

function sanitizeSmtpSetting(setting: SmtpSetting | null): SmtpSetting | null {
  if (!setting) return null

  const safeSetting = { ...setting }
  delete safeSetting.password
  return safeSetting
}

function sanitizeWebhookSettings(settings: unknown): WebhookSetting[] {
  return normalizeList<WebhookSetting>(settings).map((webhook) => {
    const safeWebhook = { ...webhook } as WebhookSetting & { secret?: unknown }
    delete safeWebhook.secret
    return safeWebhook
  })
}

function sanitizeOpenAISetting(setting: unknown): OpenAISetting | null {
  if (!setting || typeof setting !== "object") return null

  const safeSetting = { ...(setting as OpenAISetting & { api_key?: unknown }) }
  delete safeSetting.api_key
  return safeSetting
}

function normalizeList<T>(result: unknown): T[] {
  return Array.isArray(result) ? result : []
}

function normalizeQueryRules(result: unknown): QueryRule[] {
  return normalizeList<QueryRule>(result).map((rule) => ({
    ...rule,
    search_type: normalizeSearchType(rule.search_type),
    analysis_enabled: Boolean(rule.analysis_enabled),
  }))
}

function normalizeSearchType(value: unknown): QueryRuleSearchType {
  return value === "repositories" ? "repositories" : "code"
}
