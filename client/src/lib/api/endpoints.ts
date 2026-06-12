const apiUri = "/api"

export const endpoints = {
  trend: `${apiUri}/trend`,
  statistic: `${apiUri}/statistic`,
  leakage: `${apiUri}/leakage`,
  leakageInfo: `${apiUri}/leakage/info`,
  leakageCode: `${apiUri}/leakage/code`,
  settingBlacklist: `${apiUri}/setting/blacklist`,
  settingQuery: `${apiUri}/setting/query`,
  settingCron: `${apiUri}/setting/cron`,
  settingNotice: `${apiUri}/setting/notice`,
  settingMail: `${apiUri}/setting/mail`,
  settingWebhook: `${apiUri}/setting/webhook`,
  settingGithub: `${apiUri}/setting/github`,
  health: `${apiUri}/health`,
} as const
