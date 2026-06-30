import { useEffect, useRef } from "react"
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
  selectedIds: Set<string>
  onToggleSelection: (leakageId: string, selected: boolean) => void
  onTogglePageSelection: (selected: boolean) => void
}

export function ResultsTable({
  results,
  loading,
  error,
  onMarkIgnored,
  selectedIds,
  onToggleSelection,
  onTogglePageSelection,
}: ResultsTableProps) {
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

  const selectedCount = results.filter((item) => selectedIds.has(item._id)).length
  const allSelected = selectedCount === results.length
  const partiallySelected = selectedCount > 0 && !allSelected

  return (
    <div className="divide-y divide-border">
      <div className="hidden gap-3 bg-surface-subtle px-4 py-2 text-xs font-semibold text-muted-foreground lg:grid lg:grid-cols-[2rem_8.5rem_8.5rem_minmax(10rem,1fr)_minmax(12rem,1.1fr)_5rem_6.5rem_5rem_13rem] lg:items-center">
        <SelectionCheckbox
          ariaLabel={allSelected ? "取消选择本页泄露结果" : "选择本页泄露结果"}
          checked={allSelected}
          indeterminate={partiallySelected}
          onChange={(selected) => onTogglePageSelection(selected)}
        />
        <div>发现时间</div>
        <div>更新时间</div>
        <div>仓库</div>
        <div>文件</div>
        <div>语言</div>
        <div>标签</div>
        <div>状态</div>
        <div className="text-right">操作</div>
      </div>
      {results.map((item) => {
        const projectUrl = getExternalUrl(item.project_url)
        const sourceUrl = getExternalUrl(item.link)
        const quickCheckUrl = projectUrl
          ? `${projectUrl}/search?utf8=%E2%9C%93&q=pass%20OR%20password%20OR%20passwd%20OR%20pwd%20OR%20smtp%20OR%20database`
          : ""

        return (
          <article
            key={item._id}
            className="grid gap-3 px-4 py-3 transition-colors hover:bg-hover-surface/60 lg:grid-cols-[2rem_8.5rem_8.5rem_minmax(10rem,1fr)_minmax(12rem,1.1fr)_5rem_6.5rem_5rem_13rem] lg:items-center"
          >
            <SelectionCheckbox
              ariaLabel={`选择 ${item.project || item._id}`}
              checked={selectedIds.has(item._id)}
              onChange={(selected) => onToggleSelection(item._id, selected)}
            />
            <div className="text-xs text-muted-foreground">{formatDateTime(item.discovered_at)}</div>
            <div className="text-xs text-muted-foreground">{formatDateTime(item.datetime)}</div>

            <div className="min-w-0">
              <span className="block truncate text-sm font-semibold">{item.project || "未知仓库"}</span>
            </div>

            <div className="min-w-0">
              <span className="block truncate text-xs text-muted-foreground">{item.filepath || item.filename || "未知文件"}</span>
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
                  <Button variant="ghost" size="icon-sm" asChild>
                    <Link to={`/view/leakage/${item._id}`} aria-label="查看泄露详情代码">
                      <FileCode className="size-4" aria-hidden="true" />
                    </Link>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>泄露详情代码</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" disabled={!sourceUrl} asChild={Boolean(sourceUrl)}>
                    {sourceUrl ? (
                      <a href={sourceUrl} target="_blank" rel="noreferrer noopener" aria-label="GitHub 源代码">
                        <ExternalLink className="size-4" aria-hidden="true" />
                      </a>
                    ) : (
                      <ExternalLink className="size-4" aria-hidden="true" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>GitHub 源代码</TooltipContent>
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

function SelectionCheckbox({
  ariaLabel,
  checked,
  indeterminate = false,
  onChange,
}: {
  ariaLabel: string
  checked: boolean
  indeterminate?: boolean
  onChange: (selected: boolean) => void
}) {
  const ref = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (ref.current) {
      ref.current.indeterminate = indeterminate
    }
  }, [indeterminate])

  return (
    <input
      ref={ref}
      type="checkbox"
      aria-label={ariaLabel}
      checked={checked}
      onChange={(event) => onChange(event.currentTarget.checked)}
      className="size-4 rounded border-border text-primary accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
    />
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
