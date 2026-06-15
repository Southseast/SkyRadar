import { Code2, KeyRound, Plus, Trash2 } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useMemo, useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { SettingsBox, SettingsBoxRow, SettingsRowTitle } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { addGithubAccount, deleteGithubAccount, fetchGithubAccounts } from "@/lib/api/settings"
import type { GithubAccount } from "@/types/api"

const emptyForm = {
  username: "",
  password: "",
}

export function GithubAccounts() {
  const [accounts, setAccounts] = useState<GithubAccount[]>([])
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingUsername, setDeletingUsername] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadAccounts() {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchGithubAccounts()
        if (mounted) setAccounts(result)
      } catch (requestError) {
        if (mounted) {
          setAccounts([])
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadAccounts()

    return () => {
      mounted = false
    }
  }, [])

  const canSubmit = useMemo(() => Boolean(form.username.trim() && form.password.trim()), [form.password, form.username])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice(null)
    setError(null)

    if (!canSubmit) {
      setError("请输入 GitHub 账号和密码或 token。")
      return
    }

    setSaving(true)
    try {
      const response = await addGithubAccount({
        username: form.username.trim(),
        password: form.password,
      })
      setAccounts(await fetchGithubAccounts())
      setForm(emptyForm)
      setNotice(response.message ?? "添加成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(username: string) {
    setNotice(null)
    setError(null)
    setDeletingUsername(username)
    try {
      const response = await deleteGithubAccount(username)
      setAccounts((current) => current.filter((account) => account.username !== username))
      setNotice(response.message ?? "删除成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setDeletingUsername(null)
    }
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
          <SettingsRowTitle icon={Code2}>添加 GitHub 账号</SettingsRowTitle>
          <form className="grid gap-3 lg:grid-cols-[1fr_1fr_auto] lg:items-end" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <Label htmlFor="github-username">账号</Label>
              <Input
                id="github-username"
                value={form.username}
                onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                placeholder="GitHub 用户名"
                autoComplete="username"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="github-password">密码或 token</Label>
              <Input
                id="github-password"
                type="password"
                value={form.password}
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="仅用于提交到后端"
                autoComplete="current-password"
              />
            </div>
            <Button type="submit" className="rounded-md" disabled={saving}>
              <Plus className="size-4" aria-hidden="true" />
              {saving ? "添加中" : "添加"}
            </Button>
          </form>
        </SettingsBoxRow>

        <SettingsBoxRow className="space-y-3">
          <SettingsRowTitle icon={KeyRound}>已配置账号</SettingsRowTitle>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-10 rounded" />
            </div>
          ) : accounts.length ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-surface-subtle">
                    <TableHead className="min-w-[180px]">账号</TableHead>
                    <TableHead className="min-w-[160px]">密码</TableHead>
                    <TableHead className="min-w-[220px]">搜索配额</TableHead>
                    <TableHead className="min-w-[110px] text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {accounts.map((account) => (
                    <TableRow key={account.username}>
                      <TableCell className="font-medium">{account.username}</TableCell>
                      <TableCell className="font-mono text-xs">{account.mask_password ?? "******"}</TableCell>
                      <TableCell>
                        <Quota account={account} />
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-md text-risk hover:text-risk"
                          disabled={deletingUsername === account.username}
                          onClick={() => handleDelete(account.username)}
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
              <p className="text-sm font-medium">暂无 GitHub 账号</p>
              <p className="mt-1 text-xs text-muted-foreground">添加账号后，扫描任务才能使用对应额度。</p>
            </div>
          )}
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}

function Quota({ account }: { account: GithubAccount }) {
  const limit = account.rate_limit ?? 0
  const remaining = account.rate_remaining ?? 0
  const percentage = limit > 0 ? Math.max(0, Math.min(100, Math.round((remaining / limit) * 100))) : 0

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>剩余 {remaining.toLocaleString("zh-CN")}</span>
        <span>{limit.toLocaleString("zh-CN")}</span>
      </div>
      <Progress value={percentage} aria-label={`GitHub 搜索配额剩余 ${percentage}%`} />
    </div>
  )
}
