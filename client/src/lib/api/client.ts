import axios from "axios"

import type { ApiErrorBody, ApiMeta, ApiMutationResult, ApiResponse } from "@/types/api"

export const apiClient = axios.create({
  timeout: 30_000,
})

export function getResponseData<T>(body: ApiResponse<T> | null | undefined): T | null {
  if (!body || typeof body !== "object" || !("data" in body)) {
    return null
  }

  return body.data ?? null
}

export function getResponseMeta(body: { meta?: ApiMeta } | null | undefined): ApiMeta {
  return body?.meta ?? {}
}

export function toMutationResult<T>(result?: T, message = "操作成功"): ApiMutationResult<T> {
  return {
    data: result,
    message,
  }
}

export function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiErrorBody | undefined
    const message = data?.message
    if (message) {
      return data?.request_id ? `${message}（请求 ID: ${data.request_id}）` : message
    }
    if (typeof data?.detail === "string" && data.detail.trim()) return data.detail
    if (data?.error) return data.error
    if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
      return "无法连接后端服务，请确认 API 服务已启动。"
    }

    return error.message || "请求失败"
  }

  if (error instanceof Error) {
    return error.message
  }

  return "请求失败"
}
