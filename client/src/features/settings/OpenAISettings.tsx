import { Brain, Save } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { SettingsBox, SettingsBoxRow, SettingsRowTitle } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { fetchOpenAISetting, saveOpenAISetting } from "@/lib/api/settings"
import type { OpenAISettingPayload } from "@/types/api"

const defaultForm: OpenAISettingPayload = {
  enabled: false,
  api_key: "",
  base_url: "https://api.openai.com/v1",
  model: "gpt-4o-mini",
  prompt: "你是安全分析助手，请简要分析以下 GitHub 泄露发现，判断风险等级并给出处置建议。",
  notify_webhook_on_useful: false,
  usefulness_prompt: "",
  interests: "",
  max_context_lines: 120,
  max_context_chars: 12000,
  timeout_seconds: 30,
  max_retries: 2,
  concurrency: 2,
}

export function OpenAISettings() {
  const [form, setForm] = useState(defaultForm)
  const [maskApiKey, setMaskApiKey] = useState("")
  const [hasApiKey, setHasApiKey] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadSetting() {
      setLoading(true)
      setError(null)
      try {
        const setting = await fetchOpenAISetting()
        if (!mounted || !setting) return
        setForm({
          enabled: setting.enabled,
          api_key: "",
          base_url: setting.base_url,
          model: setting.model,
          prompt: setting.prompt,
          notify_webhook_on_useful: setting.notify_webhook_on_useful,
          usefulness_prompt: setting.usefulness_prompt,
          interests: setting.interests,
          max_context_lines: setting.max_context_lines,
          max_context_chars: setting.max_context_chars,
          timeout_seconds: setting.timeout_seconds,
          max_retries: setting.max_retries,
          concurrency: setting.concurrency,
        })
        setMaskApiKey(setting.mask_api_key ?? "")
        setHasApiKey(setting.has_api_key)
      } catch (requestError) {
        if (mounted) setError(getErrorMessage(requestError))
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadSetting()

    return () => {
      mounted = false
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setNotice(null)
    setError(null)

    try {
      const response = await saveOpenAISetting(form)
      const setting = response.data
      if (setting) {
        setMaskApiKey(setting.mask_api_key ?? "")
        setHasApiKey(setting.has_api_key)
        setForm((current) => ({ ...current, api_key: "" }))
      }
      setNotice(response.message ?? "设置成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  function updateNumber(key: keyof OpenAISettingPayload, value: string) {
    setForm((current) => ({ ...current, [key]: Number.parseInt(value, 10) || 0 }))
  }

  if (loading) {
    return (
      <SettingsBox>
        <SettingsBoxRow className="space-y-3">
          <Skeleton className="h-10 rounded" />
          <Skeleton className="h-28 rounded" />
          <Skeleton className="h-10 rounded" />
        </SettingsBoxRow>
      </SettingsBox>
    )
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
          <SettingsRowTitle icon={Brain}>OpenAI SDK</SettingsRowTitle>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)_220px] lg:items-end">
              <div className="grid gap-1.5">
                <Label htmlFor="openai-enabled">启用状态</Label>
                <label className="flex h-9 items-center gap-2 text-sm">
                  <Switch id="openai-enabled" checked={form.enabled} onCheckedChange={(enabled) => setForm((current) => ({ ...current, enabled }))} />
                  启用
                </label>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="openai-api-key">API Key</Label>
                <Input
                  id="openai-api-key"
                  className="h-9 rounded-md"
                  value={form.api_key}
                  onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))}
                  placeholder={hasApiKey ? maskApiKey || "已配置" : "sk-..."}
                  type="password"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="openai-model">模型</Label>
                <Input
                  id="openai-model"
                  className="h-9 rounded-md"
                  value={form.model}
                  onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))}
                />
              </div>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="openai-base-url">Base URL</Label>
              <Input
                id="openai-base-url"
                className="h-9 rounded-md"
                value={form.base_url}
                onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))}
              />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="openai-prompt">自定义 Prompt</Label>
              <Textarea
                id="openai-prompt"
                className="h-32 min-h-32 resize-y overflow-auto rounded-md [field-sizing:fixed]"
                value={form.prompt}
                onChange={(event) => setForm((current) => ({ ...current, prompt: event.target.value }))}
              />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="openai-useful-webhook">Webhook Gate</Label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Switch
                  id="openai-useful-webhook"
                  checked={form.notify_webhook_on_useful}
                  onCheckedChange={(notify_webhook_on_useful) => setForm((current) => ({ ...current, notify_webhook_on_useful }))}
                />
                有用才推送
              </label>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="openai-usefulness-prompt">项目有用性 Prompt</Label>
              <Textarea
                id="openai-usefulness-prompt"
                className="h-80 min-h-80 resize-y overflow-auto rounded-md font-mono text-xs leading-5 [field-sizing:fixed]"
                value={form.usefulness_prompt}
                onChange={(event) => setForm((current) => ({ ...current, usefulness_prompt: event.target.value }))}
              />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="openai-interests">兴趣描述</Label>
              <Textarea
                id="openai-interests"
                className="h-80 min-h-80 resize-y overflow-auto rounded-md font-mono text-xs leading-5 [field-sizing:fixed]"
                value={form.interests}
                onChange={(event) => setForm((current) => ({ ...current, interests: event.target.value }))}
              />
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <NumberField id="openai-context-lines" label="上下文行数" value={form.max_context_lines} onChange={(value) => updateNumber("max_context_lines", value)} />
              <NumberField id="openai-context-chars" label="上下文字符" value={form.max_context_chars} onChange={(value) => updateNumber("max_context_chars", value)} />
              <NumberField id="openai-timeout" label="超时秒数" value={form.timeout_seconds} onChange={(value) => updateNumber("timeout_seconds", value)} />
              <NumberField id="openai-retries" label="重试次数" value={form.max_retries} onChange={(value) => updateNumber("max_retries", value)} />
              <NumberField id="openai-concurrency" label="全局并发" value={form.concurrency} onChange={(value) => updateNumber("concurrency", value)} />
            </div>

            <Button type="submit" className="h-9 rounded-md" disabled={saving}>
              <Save className="size-4" aria-hidden="true" />
              {saving ? "保存中" : "保存设置"}
            </Button>
          </form>
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}

function NumberField({ id, label, value, onChange }: { id: string; label: string; value: number; onChange: (value: string) => void }) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} className="h-9 rounded-md" type="number" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}
