import { useCallback, useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"

import { CheckSquare, ShieldCheck, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ResultsDashboard } from "@/features/results/ResultsDashboard"
import { ResultsFilters } from "@/features/results/ResultsFilters"
import { ResultsTable } from "@/features/results/ResultsTable"
import { parseResultQuery, resultStatusToApiStatus, toSearchParams, type ResultQueryState } from "@/features/results/query"
import { SettingsBox, SettingsBoxRow } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { fetchLeakages, fetchStatistics, fetchTrend, patchLeakage } from "@/lib/api/results"
import type { Leakage, StatisticItem, TrendData } from "@/types/api"

const pageSizes = [10, 20, 50, 100]

export function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryState = useMemo(() => parseResultQuery(searchParams), [searchParams])
  const [trend, setTrend] = useState<TrendData | null>(null)
  const [results, setResults] = useState<Leakage[]>([])
  const [total, setTotal] = useState(0)
  const [tagOptions, setTagOptions] = useState<StatisticItem[]>([])
  const [languageOptions, setLanguageOptions] = useState<StatisticItem[]>([])
  const [loadingTrend, setLoadingTrend] = useState(true)
  const [loadingResults, setLoadingResults] = useState(true)
  const [resultError, setResultError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [batchLoading, setBatchLoading] = useState(false)

  const updateQuery = useCallback(
    (next: ResultQueryState) => {
      setSearchParams(toSearchParams(next))
    },
    [setSearchParams],
  )

  const loadTrend = useCallback(async () => {
    setLoadingTrend(true)
    try {
      setTrend(await fetchTrend(queryState.tag))
    } catch {
      setTrend(null)
    } finally {
      setLoadingTrend(false)
    }
  }, [queryState.tag])

  const loadResults = useCallback(async () => {
    setLoadingResults(true)
    setResultError(null)
    try {
      const response = await fetchLeakages({
        status: resultStatusToApiStatus(queryState.status),
        tag: queryState.tag,
        language: queryState.language,
        page: queryState.page,
        page_size: queryState.limit,
      })
      setResults(response.result)
      setTotal(response.total)
      setSelectedIds((current) => {
        const currentPageIds = new Set(response.result.map((item) => item._id))
        const next = new Set([...current].filter((id) => currentPageIds.has(id)))
        return next.size === current.size ? current : next
      })
    } catch (requestError) {
      setResults([])
      setTotal(0)
      setSelectedIds(new Set())
      setResultError(getErrorMessage(requestError))
    } finally {
      setLoadingResults(false)
    }
  }, [queryState])

  useEffect(() => {
    void Promise.resolve().then(() => {
      void loadTrend()
      void loadResults()
    })
  }, [loadResults, loadTrend])

  useEffect(() => {
    let mounted = true

    async function loadStatistics() {
      try {
        const [tags, languages] = await Promise.all([
          fetchStatistics("tag", queryState.tag),
          fetchStatistics("language", queryState.tag),
        ])

        if (mounted) {
          setTagOptions(tags)
          setLanguageOptions(languages)
        }
      } catch {
        if (mounted) {
          setTagOptions([])
          setLanguageOptions([])
        }
      }
    }

    void loadStatistics()
    return () => {
      mounted = false
    }
  }, [queryState.tag])

  const pageCount = Math.max(1, Math.ceil(total / queryState.limit))
  const selectedItems = results.filter((item) => selectedIds.has(item._id))
  const selectedCount = selectedItems.length

  function handleToggleSelection(leakageId: string, selected: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (selected) {
        next.add(leakageId)
      } else {
        next.delete(leakageId)
      }
      return next
    })
  }

  function handleTogglePageSelection(selected: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (selected) {
        results.forEach((item) => next.add(item._id))
      } else {
        results.forEach((item) => next.delete(item._id))
      }
      return next
    })
  }

  function clearSelection() {
    setSelectedIds(new Set())
  }

  async function handleMarkIgnored(leakage: Leakage) {
    setNotice(null)
    try {
      await patchLeakage({
        id: leakage._id,
        project: leakage.project,
        ignore: 1,
        security: 1,
        desc: leakage.desc ?? "",
      })
      setNotice("处理成功")
      setSelectedIds((current) => {
        const next = new Set(current)
        next.delete(leakage._id)
        return next
      })
      await Promise.all([loadResults(), loadTrend()])
    } catch (requestError) {
      setResultError(getErrorMessage(requestError))
    }
  }

  async function handleBatchMarkIgnored() {
    if (!selectedItems.length) return

    setNotice(null)
    setResultError(null)
    setBatchLoading(true)
    try {
      await Promise.all(
        selectedItems.map((leakage) =>
          patchLeakage({
            id: leakage._id,
            project: leakage.project,
            ignore: 1,
            security: 1,
            desc: leakage.desc ?? "",
          }),
        ),
      )
      setNotice(`已批量标记 ${selectedItems.length} 条为误报`)
      clearSelection()
      await Promise.all([loadResults(), loadTrend()])
    } catch (requestError) {
      setResultError(getErrorMessage(requestError))
    } finally {
      setBatchLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <section className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-normal">项目发现</h1>
          <p className="mt-1 text-sm text-muted-foreground">按规则、语言和处理状态筛选新发现的 GitHub 开源项目。</p>
        </div>
        {notice ? <div className="rounded border border-safe/20 bg-safe-bg px-3 py-1.5 text-sm text-safe">{notice}</div> : null}
      </section>

      <ResultsDashboard trend={trend} loading={loadingTrend} />

      <SettingsBox>
        <SettingsBoxRow>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">开源项目</h2>
            <p className="text-xs text-muted-foreground">共 {total.toLocaleString("zh-CN")} 条</p>
          </div>
          <ResultsFilters state={queryState} tagOptions={tagOptions} languageOptions={languageOptions} onChange={updateQuery} />
        </SettingsBoxRow>
        <SettingsBoxRow className="py-2">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckSquare className="size-4" aria-hidden="true" />
              <span>已选择 {selectedCount.toLocaleString("zh-CN")} 条</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" className="rounded-md" disabled={!selectedCount || batchLoading} onClick={clearSelection}>
                <X className="size-4" aria-hidden="true" />
                清空选择
              </Button>
              <Button variant="outline" size="sm" className="rounded-md" disabled={!selectedCount || batchLoading} onClick={handleBatchMarkIgnored}>
                <ShieldCheck className="size-4" aria-hidden="true" />
                {batchLoading ? "处理中" : "批量误报"}
              </Button>
            </div>
          </div>
        </SettingsBoxRow>
        <SettingsBoxRow className="p-0">
          <ResultsTable
            results={results}
            loading={loadingResults}
            error={resultError}
            onMarkIgnored={handleMarkIgnored}
            selectedIds={selectedIds}
            onToggleSelection={handleToggleSelection}
            onTogglePageSelection={handleTogglePageSelection}
          />
        </SettingsBoxRow>
        <SettingsBoxRow>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>每页</span>
              <Select
                value={String(queryState.limit)}
                onValueChange={(value) => updateQuery({ ...queryState, page: 1, limit: Number.parseInt(value, 10) })}
              >
                <SelectTrigger className="h-8 w-24 rounded-md">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {pageSizes.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                className="rounded-md"
                disabled={queryState.page <= 1}
                onClick={() => updateQuery({ ...queryState, page: queryState.page - 1 })}
              >
                上一页
              </Button>
              <span className="min-w-20 text-center text-sm text-muted-foreground">
                {queryState.page} / {pageCount}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="rounded-md"
                disabled={queryState.page >= pageCount}
                onClick={() => updateQuery({ ...queryState, page: queryState.page + 1 })}
              >
                下一页
              </Button>
            </div>
          </div>
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}
