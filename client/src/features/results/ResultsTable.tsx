import { ExternalLink, FileCode, Search, ShieldCheck } from "lucide-react"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { formatDateTime } from "@/features/results/format"
import type { Leakage } from "@/types/api"

interface ResultsTableProps {
  results: Leakage[]
  loading: boolean
  error?: string | null
  onMarkIgnored: (leakage: Leakage) => void
}

export function ResultsTable({ results, loading, error, onMarkIgnored }: ResultsTableProps) {
  if (loading) {
    return (
      <div className="divide-y divide-border">
        <div className="p-4">
          <Skeleton className="h-16 rounded" />
        </div>
        <div className="p-4">
          <Skeleton className="h-16 rounded" />
        </div>
        <div className="p-4">
          <Skeleton className="h-16 rounded" />
        </div>
      </div>
    )
  }

  if (error) {
    return <div className="p-6 text-sm text-risk">{error}</div>
  }

  if (!results.length) {
    return (
      <div className="p-8 text-center">
        <p className="text-sm font-medium">暂无匹配项目</p>
        <p className="mt-1 text-xs text-muted-foreground">当前筛选条件下没有待处理结果。</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-border">
      <div className="hidden gap-3 bg-surface-subtle px-4 py-2 text-xs font-semibold text-muted-foreground lg:grid lg:grid-cols-[9rem_minmax(18rem,1fr)_6rem_8rem_6rem_9rem] lg:items-center">
        <div>发现时间</div>
        <div>仓库 / 文件</div>
        <div>语言</div>
        <div>标签</div>
        <div>状态</div>
        <div className="text-right">操作</div>
      </div>
      {results.map((item) => {
        const projectUrl = getExternalUrl(item.project_url)
        const commitsUrl = getGithubCommitsUrl(item.project)
        const quickCheckUrl = projectUrl
          ? `${projectUrl}/search?utf8=%E2%9C%93&q=pass%20OR%20password%20OR%20passwd%20OR%20pwd%20OR%20smtp%20OR%20database`
          : ""

        return (
          <article
            key={item._id}
            className="grid gap-3 px-4 py-3 transition-colors hover:bg-hover-surface/60 lg:grid-cols-[9rem_minmax(18rem,1fr)_6rem_8rem_6rem_9rem] lg:items-center"
          >
            <div className="text-xs text-muted-foreground">{formatDateTime(item.datetime)}</div>

            <div className="min-w-0">
              {projectUrl ? (
                <a
                  href={projectUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="block truncate text-sm font-semibold text-info hover:underline"
                >
                  {item.project || "未知仓库"}
                </a>
              ) : (
                <span className="block truncate text-sm font-semibold">{item.project || "未知仓库"}</span>
              )}

              <Link
                to={`/view/leakage/${item._id}`}
                className="mt-1 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
              >
                <FileCode className="size-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">{item.filepath || item.filename || "未知文件"}</span>
              </Link>
            </div>

            <div className="text-sm text-muted-foreground lg:text-foreground">{item.language || "未知"}</div>

            <div className="min-w-0">
              <Link to={`/?tag=${encodeURIComponent(item.tag || "未标记")}`} className="inline-flex max-w-full">
                <Badge variant="outline" className="max-w-full rounded">
                  <span className="truncate">{item.tag || "未标记"}</span>
                </Badge>
              </Link>
            </div>

            <div>{renderStatus(item)}</div>

            <div className="flex flex-wrap items-center gap-1.5 lg:justify-end">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" disabled={!commitsUrl} asChild={Boolean(commitsUrl)}>
                    {commitsUrl ? (
                      <a href={commitsUrl} target="_blank" rel="noreferrer noopener" aria-label="查看 commits">
                        <ExternalLink className="size-4" aria-hidden="true" />
                      </a>
                    ) : (
                      <ExternalLink className="size-4" aria-hidden="true" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Commits</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" disabled={!quickCheckUrl} asChild={Boolean(quickCheckUrl)}>
                    {quickCheckUrl ? (
                      <a href={quickCheckUrl} target="_blank" rel="noreferrer noopener" aria-label="快速排查">
                        <Search className="size-4" aria-hidden="true" />
                      </a>
                    ) : (
                      <Search className="size-4" aria-hidden="true" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>快速排查</TooltipContent>
              </Tooltip>
              <Button variant="outline" size="sm" className="rounded-md" onClick={() => onMarkIgnored(item)}>
                <ShieldCheck className="size-4" aria-hidden="true" />
                误报
              </Button>
            </div>
          </article>
        )
      })}
    </div>
  )
}

function renderStatus(item: Leakage) {
  if (item.security === 1) {
    return <Badge className="rounded bg-safe-bg text-safe hover:bg-safe-bg">误报</Badge>
  }

  if (item.desc) {
    return <Badge className="rounded bg-risk-bg text-risk hover:bg-risk-bg">确认</Badge>
  }

  return <Badge className="rounded bg-warning-bg text-warning hover:bg-warning-bg">待审</Badge>
}

function getExternalUrl(value?: string | null) {
  return value && value.trim() ? value : ""
}

function getGithubCommitsUrl(project?: string | null) {
  if (!project || !project.includes("/")) return ""

  return `https://github.com/${project}/commits`
}
