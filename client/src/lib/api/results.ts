import { apiClient, getResponseData, getResponseMeta, toMutationResult } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import type {
  AffectedAsset,
  ApiResponse,
  Leakage,
  LeakageCode,
  LeakageDetailForm,
  LeakageListParams,
  LeakagePatchPayload,
  StatisticItem,
  TrendData,
} from "@/types/api"

const emptyTrendCount = {
  total: 0,
  ignore: 0,
  risk: 0,
}

const defaultTrend: TrendData = {
  all: { ...emptyTrendCount },
  today: { ...emptyTrendCount },
  engine: {
    status: false,
    last: 0,
  },
}

export async function fetchTrend(tag?: string) {
  const response = await apiClient.get<ApiResponse<TrendData>>(endpoints.trends, {
    params: { tag: tag || undefined },
  })

  return normalizeTrend(getResponseData(response.data))
}

export async function fetchStatistics(by: "tag" | "language", tag?: string) {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.statistics, {
    params: { by, tag: tag || "" },
  })

  return normalizeList<StatisticItem>(getResponseData(response.data))
}

export async function fetchLeakages(params: LeakageListParams) {
  const response = await apiClient.get<ApiResponse<unknown>>(endpoints.leakages, {
    params: {
      security: params.status.security,
      desc_exists: params.status.desc?.$exists,
      tag: params.tag || undefined,
      language: params.language || undefined,
      page: params.page,
      page_size: params.page_size,
    },
  })
  const meta = getResponseMeta(response.data)

  return {
    result: normalizeList<Leakage>(getResponseData(response.data)).map(normalizeLeakage),
    total: toNumber(meta.total, 0),
  }
}

export async function patchLeakage(payload: LeakagePatchPayload) {
  const { id, ...body } = payload
  const response = await apiClient.patch<ApiResponse<unknown>>(endpoints.leakage(id), body)
  return toMutationResult(getResponseData(response.data), "处理成功")
}

export async function fetchLeakageInfo(id: string) {
  const response = await apiClient.get<ApiResponse<Leakage | null>>(endpoints.leakage(id))
  const data = getResponseData(response.data)

  return data ? normalizeLeakage(data) : null
}

export async function fetchLeakageCode(id: string) {
  const response = await apiClient.get<ApiResponse<LeakageCode | null>>(endpoints.leakageCode(id))

  return normalizeLeakageCode(getResponseData(response.data))
}

export async function patchLeakageDetail(payload: LeakageDetailForm) {
  const { id, ...body } = payload
  const response = await apiClient.patch<ApiResponse<unknown>>(endpoints.leakage(id), body)
  return toMutationResult(getResponseData(response.data), "处理成功")
}

function normalizeTrend(raw: TrendData | null | undefined): TrendData {
  return {
    all: normalizeTrendCount(raw?.all),
    today: normalizeTrendCount(raw?.today),
    engine: {
      status: typeof raw?.engine?.status === "boolean" ? raw.engine.status : defaultTrend.engine.status,
      last: toNumber(raw?.engine?.last, defaultTrend.engine.last),
    },
  }
}

function normalizeTrendCount(raw: TrendData["all"] | null | undefined) {
  return {
    total: toNumber(raw?.total, emptyTrendCount.total),
    ignore: toNumber(raw?.ignore, emptyTrendCount.ignore),
    risk: toNumber(raw?.risk, emptyTrendCount.risk),
  }
}

function normalizeLeakageCode(raw: LeakageCode | null | undefined): LeakageCode {
  return {
    code: typeof raw?.code === "string" ? raw.code : "",
    affect: normalizeAffectedAssets(raw?.affect),
  }
}

function normalizeAffectedAssets(raw: unknown): AffectedAsset[] {
  if (!Array.isArray(raw)) return []

  return raw.flatMap((item) => {
    if (typeof item === "string") {
      const value = item.trim()
      return value ? [{ type: "unknown", value }] : []
    }

    if (!item || typeof item !== "object") return []

    const asset = item as Partial<AffectedAsset>
    if (typeof asset.value !== "string") return []

    const value = asset.value.trim()
    if (!value) return []

    return [
      {
        type: typeof asset.type === "string" && asset.type.trim() ? asset.type : "unknown",
        value,
      },
    ]
  })
}

function normalizeLeakage(raw: Leakage): Leakage {
  return {
    ...raw,
    _id: normalizeText(raw._id, ""),
    link: normalizeUrl(raw.link),
    project: normalizeText(raw.project, "未知仓库"),
    project_url: normalizeUrl(raw.project_url),
    username: normalizeText(raw.username, ""),
    filepath: normalizeText(raw.filepath, raw.filename || "未知文件"),
    filename: normalizeText(raw.filename, raw.filepath || "未知文件"),
    tag: normalizeText(raw.tag, "未标记"),
  }
}

function normalizeText(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim() ? value : fallback
}

function normalizeUrl(value: unknown) {
  if (typeof value !== "string") {
    return undefined
  }

  const url = value.trim()
  if (!url || url === "undefined" || url === "null") {
    return undefined
  }

  return url
}

function normalizeList<T>(result: unknown): T[] {
  return Array.isArray(result) ? result : []
}

function toNumber(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback
}
