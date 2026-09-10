import { Edit2, ExternalLink, ListChecks, Plus, Search, Trash2 } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { SettingsBox, SettingsBoxRow, SettingsRowTitle } from "@/features/settings/SettingsSection"
import { formatCount, formatRelativeTime } from "@/features/results/format"
import { getErrorMessage } from "@/lib/api/client"
import { deleteQueryRule, fetchQueryRules, saveQueryRule } from "@/lib/api/settings"
import type { QueryRule, QueryRuleSearchType } from "@/types/api"

interface QueryRuleForm {
  tag: string
  keyword: string
  search_type: QueryRuleSearchType
  enabled: boolean
  analysis_enabled: boolean
}

const emptyForm: QueryRuleForm = {
  tag: "",
  keyword: "",
  search_type: "code",
  enabled: true,
  analysis_enabled: false,
}

const searchTypeLabel = {
  code: "Code",
  repositories: "Repositories",
} as const

function githubSearchUrl(rule: QueryRule) {
  const type = rule.search_type === "repositories" ? "repositories" : "Code"
  const sort = rule.search_type === "repositories" ? "updated" : "indexed"
  return `https://github.com/search?o=desc&q=${encodeURIComponent(rule.keyword)}&ref=searchresults&s=${sort}&type=${type}&utf8=%E2%9C%93`
}

export function QueryRules() {
  const [rules, setRules] = useState<QueryRule[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingTag, setEditingTag] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadRules() {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchQueryRules()
        if (mounted) setRules(result)
      } catch (requestError) {
        if (mounted) {
          setRules([])
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadRules()

    return () => {
      mounted = false
    }
  }, [])

  const canSubmit = useMemo(() => Boolean(form.tag.trim() && form.keyword.trim()), [form.keyword, form.tag])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice(null)
    setError(null)

    if (!canSubmit) {
      setError("请输入规则名称和关键字。")
      return
    }

    setSaving(true)
    try {
      const response = await saveQueryRule({
        tag: form.tag.trim(),
        keyword: form.keyword.trim(),
        search_type: form.search_type,
        enabled: form.enabled,
        analysis_enabled: form.analysis_enabled,
      }, editingTag ?? undefined)
      setRules(await fetchQueryRules())
      setForm(emptyForm)
      setEditingId(null)
      setEditingTag(null)
      setNotice(response.message ?? "保存成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function handleToggle(rule: QueryRule, enabled: boolean) {
    setNotice(null)
    setError(null)
    setRules((current) => current.map((item) => (item._id === rule._id ? { ...item, enabled } : item)))

    try {
      const response = await saveQueryRule({
        tag: rule.tag,
        keyword: rule.keyword,
        search_type: rule.search_type,
        enabled,
        analysis_enabled: rule.analysis_enabled,
      }, rule.tag)
      setRules(await fetchQueryRules())
      setNotice(response.message ?? "更新成功")
    } catch (requestError) {
      setRules((current) => current.map((item) => (item._id === rule._id ? { ...item, enabled: rule.enabled } : item)))
      setError(getErrorMessage(requestError))
    }
  }

  async function handleDelete(rule: QueryRule) {
    setNotice(null)
    setError(null)
    setDeletingId(rule._id)

    try {
      const response = await deleteQueryRule(rule)
      setRules((current) => current.filter((item) => item._id !== rule._id))
      setNotice(response.message ?? "删除成功")
      if (editingId === rule._id) {
        setEditingId(null)
        setEditingTag(null)
        setForm(emptyForm)
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setDeletingId(null)
    }
  }

  function startEdit(rule: QueryRule) {
    setEditingId(rule._id)
    setEditingTag(rule.tag)
    setForm({
      tag: rule.tag,
      keyword: rule.keyword,
      search_type: rule.search_type,
      enabled: rule.enabled,
      analysis_enabled: rule.analysis_enabled,
    })
  }

  function resetForm() {
    setEditingId(null)
    setEditingTag(null)
    setForm(emptyForm)
    setError(null)
    setNotice(null)
  }

  return (
    <div className="space-y-4">
      {error ? (
        <Alert variant="destructive" className="rounded-md">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {notice ? <div className="rounded border border-safe/20 bg-safe-bg px-3 py-1.5 text-sm text-safe">{notice}</div> : null}

      <SettingsBox>
        <SettingsBoxRow className="space-y-3">
          <SettingsRowTitle icon={Search}>{editingId ? "编辑查询规则" : "添加查询规则"}</SettingsRowTitle>
          <form className="grid gap-3 xl:grid-cols-[220px_170px_minmax(0,1fr)_110px_130px_auto] xl:items-end" onSubmit={handleSubmit}>
            <div className="grid gap-1.5">
              <Label htmlFor="query-rule-tag">名称</Label>
              <Input
                id="query-rule-tag"
                className="h-9 rounded-md"
                value={form.tag}
                onChange={(event) => setForm((current) => ({ ...current, tag: event.target.value }))}
                placeholder="例如 credential"
              />
            </div>
            <div className="grid gap-1.5 [&>select]:hidden">
              <Label htmlFor="query-rule-search-type">查询类型</Label>
              <Select
                value={form.search_type}
                onValueChange={(search_type) =>
                  setForm((current) => ({ ...current, search_type: search_type === "repositories" ? "repositories" : "code" }))
                }
              >
                <div className="h-9 overflow-hidden">
                  <SelectTrigger id="query-rule-search-type" className="!h-9 w-full rounded-md">
                    <SelectValue />
                  </SelectTrigger>
                </div>
                <SelectContent>
                  <SelectItem value="code">Code</SelectItem>
                  <SelectItem value="repositories">Repositories</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="query-rule-keyword">关键字</Label>
              <Input
                id="query-rule-keyword"
                value={form.keyword}
                onChange={(event) => setForm((current) => ({ ...current, keyword: event.target.value }))}
                placeholder="GitHub 搜索语法，支持 OR/AND/NOT"
                className="h-9 rounded-md"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="query-rule-enabled">启用状态</Label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Switch id="query-rule-enabled" checked={form.enabled} onCheckedChange={(enabled) => setForm((current) => ({ ...current, enabled }))} />
                启用
              </label>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="query-rule-analysis-enabled">AI 分析</Label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Switch
                  id="query-rule-analysis-enabled"
                  checked={form.analysis_enabled}
                  onCheckedChange={(analysis_enabled) => setForm((current) => ({ ...current, analysis_enabled }))}
                />
                自动
              </label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" className="h-9 rounded-md" disabled={saving}>
                <Plus className="size-4" aria-hidden="true" />
                {saving ? "保存中" : "保存"}
              </Button>
              {editingId ? (
                <Button type="button" variant="outline" className="h-9 rounded-md" onClick={resetForm}>
                  取消
                </Button>
              ) : null}
            </div>
          </form>
        </SettingsBoxRow>

        <SettingsBoxRow className="space-y-3">
          <SettingsRowTitle icon={ListChecks}>监控规则</SettingsRowTitle>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-10 rounded" />
            </div>
          ) : rules.length ? (
            <Table className="table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[16%]">名称</TableHead>
                  <TableHead className="w-[34%]">查询</TableHead>
                  <TableHead className="w-[14%]">抓取进度</TableHead>
                  <TableHead className="w-[10%]">状态</TableHead>
                  <TableHead className="w-[10%]">AI 分析</TableHead>
                  <TableHead className="w-[16%] text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule._id}>
                    <TableCell className="min-w-0">
                      <Link to={`/?tag=${encodeURIComponent(rule.tag)}`}>
                        <Badge variant="outline" className="max-w-full rounded">
                          <span className="truncate">{rule.tag}</span>
                        </Badge>
                      </Link>
                    </TableCell>
                    <TableCell className="min-w-0 whitespace-normal">
                      <div className="flex min-w-0 flex-col gap-1">
                        <Badge variant="secondary" className="w-fit rounded">
                          {searchTypeLabel[rule.search_type]}
                        </Badge>
                        <a
                          className="inline-flex min-w-0 items-center gap-1 text-info hover:underline"
                          href={githubSearchUrl(rule)}
                          target="_blank"
                          rel="noreferrer noopener"
                        >
                          <span className="truncate">{rule.keyword}</span>
                          <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
                        </a>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal text-sm">
                      <div className="space-y-0.5">
                        <div>
                          {formatCount(rule.found_total)} / {formatCount(rule.api_total)}
                        </div>
                        <div className="text-xs text-muted-foreground">{formatRelativeTime(rule.last)}</div>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={rule.enabled}
                          onCheckedChange={(enabled) => void handleToggle(rule, enabled)}
                          aria-label={`${rule.tag} 启用状态`}
                        />
                        <span className="hidden text-xs text-muted-foreground sm:inline">{rule.enabled ? "启用" : "停用"}</span>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <Badge variant={rule.analysis_enabled ? "secondary" : "outline"} className="rounded">
                        {rule.analysis_enabled ? "自动" : "关闭"}
                      </Badge>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div className="flex flex-wrap justify-end gap-1.5">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-md max-sm:size-7 max-sm:px-0"
                          aria-label="编辑"
                          onClick={() => startEdit(rule)}
                        >
                          <Edit2 className="size-4" aria-hidden="true" />
                          <span className="hidden sm:inline">编辑</span>
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-md text-risk hover:text-risk max-sm:size-7 max-sm:px-0"
                          aria-label="删除"
                          disabled={deletingId === rule._id}
                          onClick={() => void handleDelete(rule)}
                        >
                          <Trash2 className="size-4" aria-hidden="true" />
                          <span className="hidden sm:inline">删除</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="rounded border border-dashed p-6 text-center">
              <p className="text-sm font-medium">暂无查询规则</p>
              <p className="mt-1 text-xs text-muted-foreground">添加规则后，扫描任务会按关键字查询 GitHub。</p>
            </div>
          )}
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}
