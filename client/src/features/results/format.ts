export function formatDateTime(value?: string | number | Date | null) {
  if (!value) return "-"
  const date = new Date(normalizeDateTimeInput(value))
  if (Number.isNaN(date.getTime())) return "-"

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hour = String(date.getHours()).padStart(2, "0")
  const minute = String(date.getMinutes()).padStart(2, "0")

  return `${year}-${month}-${day} ${hour}:${minute}`
}

function normalizeDateTimeInput(value: string | number | Date) {
  if (typeof value !== "string") return value
  if (!/^\d{4}-\d{2}-\d{2}T/.test(value)) return value
  if (/(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(value)) return value

  return `${value}Z`
}

export function formatRelativeTime(seconds?: number) {
  if (!seconds) return "-"
  const diffSeconds = Math.max(0, Math.floor(Date.now() / 1000 - seconds))
  if (diffSeconds < 60) return "刚刚"
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} 分钟前`
  if (diffSeconds < 86_400) return `${Math.floor(diffSeconds / 3600)} 小时前`
  return `${Math.floor(diffSeconds / 86_400)} 天前`
}

export function formatCount(value?: number) {
  return (value ?? 0).toLocaleString("zh-CN")
}
