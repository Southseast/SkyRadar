import { ListFilter, Plus, ShieldMinus, Trash2 } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { SettingsBox, SettingsBoxRow, SettingsRowTitle } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { addBlacklistItem, deleteBlacklistItem, fetchBlacklist } from "@/lib/api/settings"
import type { BlacklistItem } from "@/types/api"

export function Blacklist() {
  const [items, setItems] = useState<BlacklistItem[]>([])
  const [text, setText] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingText, setDeletingText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadBlacklist() {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchBlacklist()
        if (mounted) setItems(result)
      } catch (requestError) {
        if (mounted) {
          setItems([])
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadBlacklist()

    return () => {
      mounted = false
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)

    const value = text.trim()
    if (!value) {
      setError("请输入黑名单关键字。")
      return
    }

    setSaving(true)
    try {
      const response = await addBlacklistItem(value)
      setItems(await fetchBlacklist())
      setText("")
      setNotice(response.message ?? "添加成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(item: BlacklistItem) {
    setError(null)
    setNotice(null)
    setDeletingText(item.text)

    try {
      const response = await deleteBlacklistItem(item.text)
      setItems((current) => current.filter((currentItem) => currentItem.text !== item.text))
      setNotice(response.message ?? "删除成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setDeletingText(null)
    }
  }

  return (
    <div className="space-y-4">
      <Alert className="rounded-md border-warning/30 bg-warning-bg text-warning">
        <AlertDescription className="text-warning">项目名称或文件名包含黑名单关键字时，扫描结果不会保存。</AlertDescription>
      </Alert>
      {error ? (
        <Alert variant="destructive" className="rounded-md">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {notice ? <div className="rounded border border-safe/20 bg-safe-bg px-3 py-1.5 text-sm text-safe">{notice}</div> : null}

      <SettingsBox>
        <SettingsBoxRow className="space-y-3">
          <SettingsRowTitle icon={ShieldMinus}>添加黑名单</SettingsRowTitle>
          <form className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end lg:max-w-2xl" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <Label htmlFor="blacklist-text">关键字</Label>
              <Input
                id="blacklist-text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="项目名称或文件名关键字"
              />
            </div>
            <Button type="submit" className="rounded-md" disabled={saving}>
              <Plus className="size-4" aria-hidden="true" />
              {saving ? "添加中" : "添加"}
            </Button>
          </form>
        </SettingsBoxRow>

        <SettingsBoxRow className="space-y-3">
          <SettingsRowTitle icon={ListFilter}>关键字列表</SettingsRowTitle>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-10 rounded" />
            </div>
          ) : items.length ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-surface-subtle">
                    <TableHead className="min-w-[260px]">关键字</TableHead>
                    <TableHead className="min-w-[110px] text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.text} className="hover:bg-hover-surface/60">
                      <TableCell className="font-mono text-xs">{item.text}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-md text-risk hover:text-risk"
                          disabled={deletingText === item.text}
                          onClick={() => void handleDelete(item)}
                        >
                          <Trash2 className="size-4" aria-hidden="true" />
                          删除
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="rounded border border-dashed p-6 text-center">
              <p className="text-sm font-medium">暂无黑名单关键字</p>
              <p className="mt-1 text-xs text-muted-foreground">添加关键字后，匹配到的项目或文件会被扫描任务跳过。</p>
            </div>
          )}
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}
