const apiUri = "/api/v1"

function resourceUrl(resource: string, id: string) {
  return `${apiUri}/${resource}/${encodeURIComponent(id)}`
}

export const endpoints = {
  trends: `${apiUri}/trends`,
  statistics: `${apiUri}/statistics`,
  leakages: `${apiUri}/leakages`,
  leakage: (id: string) => resourceUrl("leakages", id),
  leakageAIAnalysis: (id: string) => `${resourceUrl("leakages", id)}/ai-analysis`,
  leakageCode: (id: string) => `${resourceUrl("leakages", id)}/code`,
  blacklistItems: `${apiUri}/blacklist-items`,
  blacklistItem: (text: string) => resourceUrl("blacklist-items", text),
  assetRules: `${apiUri}/asset-rules`,
  assetRule: (ruleId: string) => resourceUrl("asset-rules", ruleId),
  searchRules: `${apiUri}/search-rules`,
  searchRule: (tag: string) => resourceUrl("search-rules", tag),
  openAISettingsCurrent: `${apiUri}/openai-settings/current`,
  taskScheduleCurrent: `${apiUri}/task-schedules/current`,
  notificationRecipients: `${apiUri}/notification-recipients`,
  notificationRecipient: (mail: string) => resourceUrl("notification-recipients", mail),
  mailSettingsCurrent: `${apiUri}/mail-settings/current`,
  webhooks: `${apiUri}/webhooks`,
  webhook: (webhookId: string) => resourceUrl("webhooks", webhookId),
  webhookTests: `${apiUri}/webhook-tests`,
  githubAccounts: `${apiUri}/github-accounts`,
  githubAccount: (username: string) => resourceUrl("github-accounts", username),
  health: `${apiUri}/health`,
} as const
