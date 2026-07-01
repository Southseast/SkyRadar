import { Edit2, ListFilter, Plus, Regex, Trash2 } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { SettingsBox, SettingsBoxRow, SettingsRowTitle } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { deleteAssetRule, fetchAssetRules, saveAssetRule } from "@/lib/api/settings"
import type { AssetRule } from "@/types/api"

interface AssetRuleForm {
  name: string
  type: string
  pattern: string
  enabled: boolean
}

const emptyForm: AssetRuleForm = {
  name: "",
  type: "",
  pattern: "",
  enabled: true,
}

export function AssetRules() {
  const [rules, setRules] = useState<AssetRule[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
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
        const result = await fetchAssetRules()
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)

    const payload = {
      name: form.name.trim(),
      type: form.type.trim().toLowerCase(),
      pattern: form.pattern.trim(),
      enabled: form.enabled,
    }

    if (!payload.name || !payload.type || !payload.pattern) {
      setError("请输入规则名称、类型和正则表达式。")
      return
    }

    setSaving(true)
    try {
      const response = await saveAssetRule(payload, editingId ?? undefined)
      setRules(await fetchAssetRules())
      setForm(emptyForm)
      setEditingId(null)
      setNotice(response.message ?? "保存成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function handleToggle(rule: AssetRule, enabled: boolean) {
    setError(null)
    setNotice(null)
    setRules((current) => current.map((item) => (item._id === rule._id ? { ...item, enabled } : item)))

    try {
      const response = await saveAssetRule(
        {
          name: rule.name,
          type: rule.type,
          pattern: rule.pattern,
          enabled,
        },
        rule._id,
      )
      setRules(await fetchAssetRules())
      setNotice(response.message ?? "更新成功")
    } catch (requestError) {
      setRules((current) => current.map((item) => (item._id === rule._id ? { ...item, enabled: rule.enabled } : item)))
      setError(getErrorMessage(requestError))
    }
  }

  async function handleDelete(rule: AssetRule) {
    setError(null)
    setNotice(null)
    setDeletingId(rule._id)

    try {
      const response = await deleteAssetRule(rule)
      setRules((current) => current.filter((item) => item._id !== rule._id))
      setNotice(response.message ?? "删除成功")
      if (editingId === rule._id) resetForm()
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setDeletingId(null)
    }
  }

  function startEdit(rule: AssetRule) {
    setEditingId(rule._id)
    setForm({
      name: rule.name,
      type: rule.type,
      pattern: rule.pattern,
      enabled: rule.enabled,
    })
  }

  function resetForm() {
    setEditingId(null)
    setForm(emptyForm)
    setError(null)
    setNotice(null)
  }

  return (
    <div className="space-y-4">
      <Alert className="rounded-md border-info/30 bg-info-bg text-info">
        <AlertDescription className="text-info">扫描任务会按启用的正则规则提取泄露详情中的受影响资产。</AlertDescription>
      </Alert>
      {error ? (
        <Alert variant="destructive" className="rounded-md">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {notice ? <div className="rounded border border-safe/20 bg-safe-bg px-3 py-1.5 text-sm text-safe">{notice}</div> : null}

      <SettingsBox>
        <SettingsBoxRow className="space-y-3">
          <SettingsRowTitle icon={Regex}>{editingId ? "编辑资产规则" : "添加资产规则"}</SettingsRowTitle>
          <form className="grid gap-3 lg:grid-cols-[180px_140px_minmax(0,1fr)_110px_auto] lg:items-end" onSubmit={handleSubmit}>
            <div className="grid gap-1.5">
              <Label htmlFor="asset-rule-name">名称</Label>
              <Input
                id="asset-rule-name"
                className="h-9 rounded-md"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="例如 Email"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="asset-rule-type">类型</Label>
              <Input
                id="asset-rule-type"
                className="h-9 rounded-md"
                value={form.type}
                onChange={(event) => setForm((current) => ({ ...current, type: event.target.value }))}
                placeholder="email"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="asset-rule-pattern">正则表达式</Label>
              <Input
                id="asset-rule-pattern"
                className="h-9 rounded-md"
                value={form.pattern}
                onChange={(event) => setForm((current) => ({ ...current, pattern: event.target.value }))}
                placeholder="AKIA[0-9A-Z]{16}"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="asset-rule-enabled">启用状态</Label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Switch id="asset-rule-enabled" checked={form.enabled} onCheckedChange={(enabled) => setForm((current) => ({ ...current, enabled }))} />
                启用
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
          <SettingsRowTitle icon={ListFilter}>资产规则</SettingsRowTitle>
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
                  <TableHead className="w-[20%]">名称</TableHead>
                  <TableHead className="w-[14%]">类型</TableHead>
                  <TableHead className="w-[40%]">正则</TableHead>
                  <TableHead className="w-[12%]">状态</TableHead>
                  <TableHead className="w-[14%] text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule._id}>
                    <TableCell className="min-w-0">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate font-medium">{rule.name}</span>
                        {rule.builtin ? <Badge className="shrink-0 rounded bg-info-bg text-info hover:bg-info-bg">预置</Badge> : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="rounded">
                        {rule.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="min-w-0">
                      <code className="block truncate font-mono text-xs text-muted-foreground">{rule.pattern}</code>
                    </TableCell>
                    <TableCell>
                      <Switch checked={rule.enabled} onCheckedChange={(enabled) => void handleToggle(rule, enabled)} aria-label={`${rule.name} 启用状态`} />
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div className="flex flex-wrap justify-end gap-1.5">
                        <Button type="button" variant="outline" size="sm" className="rounded-md" onClick={() => startEdit(rule)}>
                          <Edit2 className="size-4" aria-hidden="true" />
                          编辑
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-md text-risk hover:text-risk"
                          disabled={deletingId === rule._id}
                          onClick={() => void handleDelete(rule)}
                        >
                          <Trash2 className="size-4" aria-hidden="true" />
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="rounded border border-dashed p-6 text-center">
              <p className="text-sm font-medium">暂无资产规则</p>
              <p className="mt-1 text-xs text-muted-foreground">添加规则后，扫描任务会按正则提取受影响资产。</p>
            </div>
          )}
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}
