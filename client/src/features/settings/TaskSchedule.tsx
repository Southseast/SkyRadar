import { Save, Timer } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { SettingsBox, SettingsBoxRow, SettingsRowTitle } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { fetchTaskSetting, saveTaskSetting } from "@/lib/api/settings"
import type { TaskSetting } from "@/types/api"

const defaults = {
  minute: 10,
  page: 1,
}

export function TaskSchedule() {
  const [form, setForm] = useState(defaults)
  const [setting, setSetting] = useState<TaskSetting | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadTaskSetting() {
      setLoading(true)
      setError(null)
      try {
        const response = await fetchTaskSetting()
        if (!mounted) return

        if (response.result) {
          setSetting(response.result)
          setForm({
            minute: response.result.minute,
            page: response.result.page,
          })
        } else {
          setSetting(null)
          setNotice(response.msg ?? "请配置查询页数和周期")
        }
      } catch (requestError) {
        if (mounted) {
          setSetting(null)
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadTaskSetting()

    return () => {
      mounted = false
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)
    setSaving(true)

    const payload = {
      minute: clampNumber(form.minute, 5, 30),
      page: clampNumber(form.page, 1, 100),
    }

    try {
      const response = await saveTaskSetting(payload)
      setForm(payload)
      setSetting((current) => ({ key: "task", pid: current?.pid, last: current?.last, ...payload }))
      setNotice(response.msg ?? "设置成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
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
          <SettingsRowTitle icon={Timer}>任务调度</SettingsRowTitle>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-10 rounded" />
              <Skeleton className="h-9 w-28 rounded" />
            </div>
          ) : (
            <form className="grid gap-4 sm:max-w-sm" onSubmit={handleSubmit}>
              <div className="grid gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="task-minute">时间间隔（分钟）</Label>
                  <Input
                    id="task-minute"
                    type="number"
                    min={5}
                    max={30}
                    step={1}
                    value={form.minute}
                    onChange={(event) => setForm((current) => ({ ...current, minute: Number(event.target.value) }))}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="task-page">页数（30条/页）</Label>
                  <Input
                    id="task-page"
                    type="number"
                    min={1}
                    max={100}
                    step={1}
                    value={form.page}
                    onChange={(event) => setForm((current) => ({ ...current, page: Number(event.target.value) }))}
                  />
                </div>
              </div>

              <div className="grid gap-3">
                <TaskSummary setting={setting} form={form} />
                <Button type="submit" className="w-fit rounded-md" disabled={saving}>
                  <Save className="size-4" aria-hidden="true" />
                  {saving ? "保存中" : "确认"}
                </Button>
              </div>
            </form>
          )}
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}

function TaskSummary({ setting, form }: { setting: TaskSetting | null; form: { minute: number; page: number } }) {
  return (
    <div className="text-sm text-muted-foreground">
      当前配置：每 {form.minute || defaults.minute} 分钟扫描 {form.page || defaults.page} 页
      {setting?.pid ? <span>，进程 PID {setting.pid}</span> : null}
    </div>
  )
}

function clampNumber(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min
  return Math.min(max, Math.max(min, Math.round(value)))
}
