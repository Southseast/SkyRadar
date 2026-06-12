import { Activity, CheckCircle2, Clock3, ShieldAlert } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { formatCount, formatRelativeTime } from "@/features/results/format"
import { SettingsBox, SettingsBoxRow } from "@/features/settings/SettingsSection"
import type { TrendData } from "@/types/api"

interface ResultsDashboardProps {
  trend?: TrendData | null
  loading: boolean
}

export function ResultsDashboard({ trend, loading }: ResultsDashboardProps) {
  const items = [
    {
      label: "泄露总数",
      value: trend?.all.total,
      footer: `今日：${formatCount(trend?.today.total)}`,
      icon: ShieldAlert,
      tone: "text-info",
    },
    {
      label: "已确认",
      value: trend?.all.risk,
      footer: `今日：${formatCount(trend?.today.risk)}`,
      icon: Clock3,
      tone: "text-risk",
    },
    {
      label: "已忽略",
      value: trend?.all.ignore,
      footer: `今日：${formatCount(trend?.today.ignore)}`,
      icon: CheckCircle2,
      tone: "text-safe",
    },
    {
      label: "查询引擎",
      value: trend?.engine.status ? "正常" : "离线",
      footer: `最近：${formatRelativeTime(trend?.engine.last)}`,
      icon: Activity,
      tone: trend?.engine.status ? "text-safe" : "text-warning",
    },
  ]

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="关键指标">
      {items.map((item) => (
        <SettingsBox key={item.label}>
          <SettingsBoxRow className="flex min-h-[96px] items-center justify-between">
            {loading ? (
              <div className="w-full space-y-2">
                <Skeleton className="h-4 w-20 rounded" />
                <Skeleton className="h-7 w-16 rounded" />
                <Skeleton className="h-3 w-24 rounded" />
              </div>
            ) : (
              <>
                <div>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                  <p className="mt-1 text-2xl font-semibold">{item.label === "查询引擎" ? item.value : formatCount(item.value as number | undefined)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{item.footer}</p>
                </div>
                <item.icon className={`size-5 ${item.tone}`} aria-hidden="true" />
              </>
            )}
          </SettingsBoxRow>
        </SettingsBox>
      ))}
    </section>
  )
}
