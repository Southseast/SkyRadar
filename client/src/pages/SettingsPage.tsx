import { Bell, Code2, Search, ShieldMinus, Timer } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useLocation, useParams } from "react-router-dom"

import { Blacklist } from "@/features/settings/Blacklist"
import { GithubAccounts } from "@/features/settings/GithubAccounts"
import { NoticeSettings } from "@/features/settings/NoticeSettings"
import { QueryRules } from "@/features/settings/QueryRules"
import { SettingsSubhead } from "@/features/settings/SettingsSection"
import { TaskSchedule } from "@/features/settings/TaskSchedule"
import { cn } from "@/lib/utils"

const settingGroups = [
  {
    label: "数据源",
    items: [{ value: "github", label: "GitHub 账号", icon: Code2 }],
  },
  {
    label: "扫描",
    items: [
      { value: "rule", label: "查询规则", icon: Search },
      { value: "task", label: "任务调度", icon: Timer },
      { value: "blacklist", label: "黑名单", icon: ShieldMinus },
    ],
  },
  {
    label: "通知",
    items: [{ value: "notice", label: "Webhook 通知", icon: Bell }],
  },
]

const settingTabs = settingGroups.flatMap((group) => group.items)
const tabs = settingTabs.map((item) => item.value)
const settingCopy: Record<string, { title: string; description: string }> = {
  github: {
    title: "GitHub 账号",
    description: "管理用于 GitHub 代码搜索的账号凭据和搜索配额。",
  },
  rule: {
    title: "查询规则",
    description: "配置 GitHub 搜索关键字，扫描任务会按启用的规则发现相关开源项目。",
  },
  task: {
    title: "任务调度",
    description: "设置自动扫描的时间间隔和每次查询页数。",
  },
  blacklist: {
    title: "黑名单",
    description: "匹配黑名单关键字的项目或文件不会保存到扫描结果。",
  },
  notice: {
    title: "Webhook 通知",
    description: "配置告警通知的接收人、SMTP 和群机器人 webhook。",
  },
}

export function SettingsPage() {
  const { tab } = useParams()
  const location = useLocation()
  const initialAnchor = getAnchor(location.hash, tab)
  const [activeAnchor, setActiveAnchor] = useState(initialAnchor)
  const sections = useMemo(() => settingTabs.map((item) => ({ ...item, ...settingCopy[item.value] })), [])

  useEffect(() => {
    const anchor = getAnchor(location.hash, tab)
    const frame = window.requestAnimationFrame(() => {
      setActiveAnchor(anchor)

      if (anchor) {
        document.getElementById(anchor)?.scrollIntoView({ block: "start" })
      }
    })

    return () => window.cancelAnimationFrame(frame)
  }, [location.hash, tab])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]

        if (visible?.target.id && tabs.includes(visible.target.id)) {
          setActiveAnchor(visible.target.id)
        }
      },
      { rootMargin: "-80px 0px -65% 0px", threshold: [0.2, 0.5, 0.8] }
    )

    for (const section of document.querySelectorAll<HTMLElement>("[data-setting-section]")) {
      observer.observe(section)
    }

    return () => observer.disconnect()
  }, [])

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)] lg:items-start">
      <nav
        aria-label="设置分类"
        className="-mx-4 overflow-x-auto border-y bg-background px-4 py-2 sm:-mx-6 sm:px-6 lg:sticky lg:top-20 lg:mx-0 lg:overflow-visible lg:border-y-0 lg:bg-transparent lg:px-0 lg:py-0"
      >
        <div className="flex min-w-max gap-1 lg:min-w-0 lg:flex-col lg:gap-4">
          {settingGroups.map((group) => (
            <div key={group.label} className="contents lg:block">
              <div className="hidden px-2 pb-1 text-xs font-semibold text-muted-foreground lg:block">{group.label}</div>
              <div className="flex gap-1 lg:flex-col">
                {group.items.map((item) => {
                  const selected = item.value === activeAnchor

                  return (
                    <a
                      key={item.value}
                      href={`/setting#${item.value}`}
                      aria-current={selected ? "location" : undefined}
                      onClick={() => setActiveAnchor(item.value)}
                      className={cn(
                        "relative inline-flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-hover-surface hover:text-foreground active:bg-selected-surface focus-visible:ring-2 focus-visible:ring-foreground/35 focus-visible:outline-none lg:w-full lg:justify-start lg:px-2",
                        selected &&
                          "bg-selected-surface font-medium text-foreground lg:after:absolute lg:after:top-1 lg:after:bottom-1 lg:after:-left-2 lg:after:w-1 lg:after:rounded-full lg:after:bg-info"
                      )}
                    >
                      <item.icon className={cn("size-4", selected ? "text-foreground" : "text-muted-foreground")} aria-hidden="true" />
                      {item.label}
                    </a>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </nav>

      <section aria-labelledby="setting-panel-title" className="min-w-0">
        <h1 id="setting-panel-title" className="sr-only">
          设置
        </h1>
        <div className="space-y-10">
          {sections.map((section) => (
            <section key={section.value} id={section.value} data-setting-section className="scroll-mt-20 space-y-4">
              <SettingsSubhead title={section.title} description={section.description} />
              <SettingPanel activeTab={section.value} />
            </section>
          ))}
        </div>
      </section>
    </div>
  )
}

function getAnchor(hash: string, tab?: string) {
  const hashValue = hash.replace(/^#/, "")
  if (tabs.includes(hashValue)) return hashValue
  if (tab && tabs.includes(tab)) return tab
  return "github"
}

function SettingPanel({ activeTab }: { activeTab: string }) {
  switch (activeTab) {
    case "rule":
      return <QueryRules />
    case "task":
      return <TaskSchedule />
    case "blacklist":
      return <Blacklist />
    case "notice":
      return <NoticeSettings />
    case "github":
    default:
      return <GithubAccounts />
  }
}
