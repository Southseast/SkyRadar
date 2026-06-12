import type { LeakageQueryStatus } from "@/types/api"

export type ResultStatusLabel = "不限" | "待审" | "确认" | "误报"

export interface ResultQueryState {
  page: number
  limit: number
  tag: string
  language: string
  status: ResultStatusLabel
}

const statusLabels: ResultStatusLabel[] = ["不限", "待审", "确认", "误报"]

export function parseResultQuery(searchParams: URLSearchParams): ResultQueryState {
  const status = searchParams.get("status")
  const limit = Number.parseInt(searchParams.get("limit") ?? "10", 10)
  const page = Number.parseInt(searchParams.get("page") ?? "1", 10)

  return {
    page: Number.isFinite(page) && page > 0 ? page : 1,
    limit: [10, 20, 50, 100].includes(limit) ? limit : 10,
    tag: searchParams.get("tag") ?? "",
    language: searchParams.get("language") ?? "",
    status: isResultStatusLabel(status) ? status : "待审",
  }
}

export function resultStatusToApiStatus(status: ResultStatusLabel): LeakageQueryStatus {
  if (status === "不限") {
    return {}
  }

  if (status === "确认") {
    return { security: 0, desc: { $exists: true } }
  }

  if (status === "误报") {
    return { security: 1 }
  }

  return { security: 0, desc: { $exists: false } }
}

export function toSearchParams(state: ResultQueryState) {
  const params = new URLSearchParams()
  params.set("page", String(state.page))
  params.set("limit", String(state.limit))

  if (state.tag) params.set("tag", state.tag)
  if (state.language) params.set("language", state.language)
  if (state.status !== "待审") params.set("status", state.status)

  return params
}

export function getStatusLabels() {
  return statusLabels
}

function isResultStatusLabel(value: string | null): value is ResultStatusLabel {
  return value !== null && statusLabels.includes(value as ResultStatusLabel)
}
