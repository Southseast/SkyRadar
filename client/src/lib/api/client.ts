import axios from "axios"

export const apiClient = axios.create({
  timeout: 30_000,
})

export function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { msg?: string } | undefined
    if (data?.msg) return data.msg
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
