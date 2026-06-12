export interface ApiResponse<T> {
  status?: number
  msg?: string
  result: T
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number
}

export interface AffectedAsset {
  type: "domain" | "email" | "ip" | string
  value: string
}

export interface Leakage {
  _id: string
  link?: string | null
  project: string
  project_url?: string | null
  language?: string | null
  username: string
  avatar_url?: string
  filepath: string
  filename: string
  security: 0 | 1
  ignore: 0 | 1
  tag: string
  desc?: string
  datetime?: string
  timestamp?: number
}

export interface LeakageQueryStatus {
  security?: 0 | 1
  desc?: {
    $exists: boolean
  }
}

export interface LeakageListParams {
  status: LeakageQueryStatus
  tag?: string
  language?: string
  limit: number
  from: number
}

export interface LeakagePatchPayload {
  id: string
  project?: string
  ignore: 0 | 1
  security: 0 | 1
  desc: string
}

export interface LeakageCode {
  code: string
  affect: AffectedAsset[]
}

export interface LeakageDetailForm {
  id: string
  project?: string
  ignore: 0 | 1
  security: 0 | 1
  desc: string
}

export interface TrendCount {
  total: number
  ignore: number
  risk: number
}

export interface TrendEngine {
  status: boolean
  last: number
}

export interface TrendData {
  all: TrendCount
  today: TrendCount
  engine: TrendEngine
}

export interface StatisticItem {
  _id: string | null
  value: number
}

export interface GithubAccount {
  username: string
  mask_password?: string
  rate_limit?: number
  rate_remaining?: number
  addat?: number
}

export interface QueryRule {
  _id: string
  keyword: string
  tag: string
  enabled: boolean
  last?: number
  status?: number
  reason?: string
  api_total?: number
  found_total?: number
}

export interface TaskSetting {
  key: "task"
  page: number
  minute: number
  pid?: number
  last?: number
}

export interface BlacklistItem {
  text: string
}

export interface NoticeMail {
  mail: string
}

export interface SmtpSetting {
  key?: "mail"
  from?: string
  host?: string
  port?: number
  tls?: boolean
  username?: string
  password?: string
  domain?: string
  enabled?: boolean
  test?: boolean
}

export type WebhookProvider = "dingtalk" | "feishu"

export interface WebhookSetting {
  provider: WebhookProvider
  webhook_url: string
  webhook_hash?: string
  secret?: string
  has_secret?: boolean
  domain?: string
  enabled?: boolean
  test?: boolean
}
