import { Bell, Bot, Mail, Plus, Send, Trash2 } from "lucide-react"
import type { Dispatch, FormEvent, SetStateAction } from "react"
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
import {
  addNoticeMail,
  deleteNoticeMail,
  deleteWebhookSetting,
  fetchNoticeMails,
  fetchSmtpSetting,
  fetchWebhookSettings,
  saveSmtpSetting,
  saveWebhookSetting,
  testWebhookSetting,
} from "@/lib/api/settings"
import type { NoticeMail, SmtpSetting, WebhookProvider, WebhookSetting } from "@/types/api"

const defaultSmtp: SmtpSetting = {
  from: "",
  host: "",
  port: 25,
  tls: false,
  username: "",
  password: "",
  domain: getDefaultDomain(),
  enabled: false,
}

const defaultWebhook: WebhookSetting = {
  provider: "dingtalk",
  webhook_url: "",
  secret: "",
  domain: getDefaultDomain(),
  enabled: true,
}

export function NoticeSettings() {
  const [mails, setMails] = useState<NoticeMail[]>([])
  const [smtp, setSmtp] = useState<SmtpSetting>(defaultSmtp)
  const [webhookSettings, setWebhookSettings] = useState<WebhookSetting[]>([])
  const [mailInput, setMailInput] = useState("")
  const [webhookForm, setWebhookForm] = useState<WebhookSetting>(defaultWebhook)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadNoticeSettings() {
      setLoading(true)
      setError(null)
      try {
        const [mailResult, smtpResult, webhookResult] = await Promise.all([
          fetchNoticeMails(),
          fetchSmtpSetting(),
          fetchWebhookSettings(),
        ])

        if (!mounted) return

        setMails(mailResult)
        if (smtpResult) setSmtp({ ...defaultSmtp, ...smtpResult })
        setWebhookSettings(webhookResult)
      } catch (requestError) {
        if (mounted) setError(getErrorMessage(requestError))
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadNoticeSettings()

    return () => {
      mounted = false
    }
  }, [])

  async function handleAddMail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const mail = mailInput.trim()
    if (!mail) {
      setError("请输入邮件接收人。")
      return
    }

    await runAction("add-mail", async () => {
      const response = await addNoticeMail(mail)
      setMails(response.result ?? [])
      setMailInput("")
      setNotice(response.msg ?? "添加成功")
    })
  }

  async function handleDeleteMail(mail: string) {
    await runAction(`delete-mail-${mail}`, async () => {
      const response = await deleteNoticeMail(mail)
      setMails(response.result ?? [])
      setNotice(response.msg ?? "删除成功")
    })
  }

  async function handleSaveSmtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction("save-smtp", async () => {
      const response = await saveSmtpSetting({
        ...smtp,
        port: Number(smtp.port) || 25,
      })
      if (response.result) setSmtp({ ...defaultSmtp, ...response.result })
      setNotice(response.msg ?? "设置成功")
    })
  }

  async function handleSaveWebhook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const webhookUrl = webhookForm.webhook_url.trim()
    const secret = webhookForm.secret?.trim() ?? ""
    if (!webhookUrl) {
      setError("请输入 webhook 地址。")
      return
    }
    if (!isWebhookUrl(webhookForm.provider, webhookUrl)) {
      setError("webhook 地址和类型不匹配。")
      return
    }
    if (!secret) {
      setError("webhook 必须配置加签 Secret。")
      return
    }

    await runAction("save-webhook", async () => {
      const response = await saveWebhookSetting({ ...webhookForm, webhook_url: webhookUrl, secret })
      setWebhookSettings(await fetchWebhookSettings())
      setWebhookForm(defaultWebhook)
      setNotice(response.msg ?? "设置成功")
    })
  }

  async function handleTestWebhook() {
    const webhookUrl = webhookForm.webhook_url.trim()
    const secret = webhookForm.secret?.trim() ?? ""
    if (!webhookUrl) {
      setError("请输入 webhook 地址。")
      return
    }
    if (!isWebhookUrl(webhookForm.provider, webhookUrl)) {
      setError("webhook 地址和类型不匹配。")
      return
    }
    if (!secret) {
      setError("webhook 必须配置加签 Secret。")
      return
    }

    await runAction("test-webhook", async () => {
      const response = await testWebhookSetting({ ...webhookForm, webhook_url: webhookUrl, secret })
      setNotice(response.msg ?? "测试消息已发送")
    })
  }

  async function handleDeleteWebhook(webhook: WebhookSetting) {
    const deleteKey = webhook.webhook_hash ?? webhook.webhook_url
    await runAction(`delete-webhook-${deleteKey}`, async () => {
      const response = await deleteWebhookSetting(webhook)
      setWebhookSettings((current) =>
        current.filter((item) =>
          webhook.webhook_hash ? item.webhook_hash !== webhook.webhook_hash : item.webhook_url !== webhook.webhook_url
        )
      )
      setNotice(response.msg ?? "删除成功")
    })
  }

  async function runAction(name: string, action: () => Promise<void>) {
    setBusy(name)
    setError(null)
    setNotice(null)
    try {
      await action()
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(null)
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

      {loading ? (
        <SettingsBox>
          <SettingsBoxRow>
            <div className="space-y-3">
              <Skeleton className="h-24 rounded" />
              <Skeleton className="h-40 rounded" />
              <Skeleton className="h-40 rounded" />
            </div>
          </SettingsBoxRow>
        </SettingsBox>
      ) : (
        <SettingsBox>
          <SmtpPanel smtp={smtp} setSmtp={setSmtp} busy={busy} onSubmit={handleSaveSmtp} />
          <MailRecipients mails={mails} mailInput={mailInput} setMailInput={setMailInput} busy={busy} onAdd={handleAddMail} onDelete={handleDeleteMail} />
          <WebhookPanel
            webhookSettings={webhookSettings}
            form={webhookForm}
            setForm={setWebhookForm}
            busy={busy}
            onSubmit={handleSaveWebhook}
            onTest={handleTestWebhook}
            onDelete={handleDeleteWebhook}
          />
        </SettingsBox>
      )}
    </div>
  )
}

function SmtpPanel({
  smtp,
  setSmtp,
  busy,
  onSubmit,
}: {
  smtp: SmtpSetting
  setSmtp: Dispatch<SetStateAction<SmtpSetting>>
  busy: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <SettingsBoxRow className="space-y-3">
      <SettingsRowTitle
        icon={Mail}
        trailing={
          <Badge className={smtp.enabled ? "rounded bg-safe-bg text-safe hover:bg-safe-bg" : "rounded bg-muted text-muted-foreground hover:bg-muted"}>
            {smtp.enabled ? "开启" : "关闭"}
          </Badge>
        }
      >
        SMTP 通知
      </SettingsRowTitle>
      <form className="grid gap-3 lg:grid-cols-2" onSubmit={onSubmit}>
        <Field id="smtp-host" label="服务器地址" value={smtp.host ?? ""} onChange={(value) => setSmtp((current) => ({ ...current, host: value }))} />
        <Field
          id="smtp-port"
          label="服务器端口"
          type="number"
          value={String(smtp.port ?? 25)}
          onChange={(value) => setSmtp((current) => ({ ...current, port: Number(value) }))}
        />
        <Field id="smtp-from" label="发件人" value={smtp.from ?? ""} onChange={(value) => setSmtp((current) => ({ ...current, from: value }))} />
        <Field id="smtp-username" label="用户名" value={smtp.username ?? ""} onChange={(value) => setSmtp((current) => ({ ...current, username: value }))} />
        <Field
          id="smtp-password"
          label="密码"
          type="password"
          value={smtp.password ?? ""}
          onChange={(value) => setSmtp((current) => ({ ...current, password: value }))}
        />
        <Field id="smtp-domain" label="监控平台地址" value={smtp.domain ?? ""} onChange={(value) => setSmtp((current) => ({ ...current, domain: value }))} />
        <div className="flex items-center gap-4">
          <SwitchField
            id="smtp-tls"
            label="TLS 加密"
            checked={Boolean(smtp.tls)}
            onCheckedChange={(tls) => setSmtp((current) => ({ ...current, tls }))}
          />
          <SwitchField
            id="smtp-enabled"
            label="开启通知"
            checked={Boolean(smtp.enabled)}
            onCheckedChange={(enabled) => setSmtp((current) => ({ ...current, enabled }))}
          />
        </div>
        <div className="flex items-end lg:justify-end">
          <Button type="submit" className="rounded-md" disabled={busy === "save-smtp"}>
            <Send className="size-4" aria-hidden="true" />
            {busy === "save-smtp" ? "保存中" : "保存 SMTP"}
          </Button>
        </div>
      </form>
    </SettingsBoxRow>
  )
}

function MailRecipients({
  mails,
  mailInput,
  setMailInput,
  busy,
  onAdd,
  onDelete,
}: {
  mails: NoticeMail[]
  mailInput: string
  setMailInput: (value: string) => void
  busy: string | null
  onAdd: (event: FormEvent<HTMLFormElement>) => void
  onDelete: (mail: string) => void
}) {
  return (
    <SettingsBoxRow className="space-y-3">
      <SettingsRowTitle icon={Mail}>邮箱通知</SettingsRowTitle>
      <form className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end lg:max-w-2xl" onSubmit={onAdd}>
        <Field id="notice-mail" label="邮箱" value={mailInput} placeholder="username@domain.com" onChange={setMailInput} />
        <Button type="submit" className="rounded-md" disabled={busy === "add-mail"}>
          <Plus className="size-4" aria-hidden="true" />
          添加
        </Button>
      </form>
      {mails.length ? (
        <Table>
          <TableHeader>
            <TableRow className="bg-surface-subtle">
              <TableHead>邮箱</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mails.map((item) => (
              <TableRow key={item.mail}>
                <TableCell>{item.mail}</TableCell>
                <TableCell className="text-right">
                  <Button type="button" variant="outline" size="sm" className="rounded-md text-risk hover:text-risk" onClick={() => onDelete(item.mail)}>
                    <Trash2 className="size-4" aria-hidden="true" />
                    删除
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <div className="rounded border border-dashed p-6 text-center text-sm text-muted-foreground">暂无邮件接收人。</div>
      )}
    </SettingsBoxRow>
  )
}

function WebhookPanel({
  webhookSettings,
  form,
  setForm,
  busy,
  onSubmit,
  onTest,
  onDelete,
}: {
  webhookSettings: WebhookSetting[]
  form: WebhookSetting
  setForm: Dispatch<SetStateAction<WebhookSetting>>
  busy: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onTest: () => void
  onDelete: (webhook: WebhookSetting) => void
}) {
  return (
    <SettingsBoxRow className="space-y-3">
      <SettingsRowTitle icon={Bot}>Webhook 通知</SettingsRowTitle>
      <form className="grid gap-3" onSubmit={onSubmit}>
        <div className="grid gap-3 lg:grid-cols-[180px_1fr]">
          <WebhookProviderSelect
            value={form.provider}
            onChange={(provider) =>
              setForm((current) => ({
                ...current,
                provider,
                webhook_url: "",
              }))
            }
          />
          <Field
            id="webhook-url"
            label="Webhook 地址"
            value={form.webhook_url}
            placeholder={webhookPlaceholder(form.provider)}
            onChange={(value) => setForm((current) => ({ ...current, webhook_url: value }))}
          />
        </div>
        <div className="grid gap-3 lg:grid-cols-[1fr_1fr_auto_auto] lg:items-end">
          <Field id="webhook-domain" label="监控平台地址" value={form.domain ?? ""} onChange={(value) => setForm((current) => ({ ...current, domain: value }))} />
          <Field
            id="webhook-secret"
            label="加签 Secret"
            type="password"
            value={form.secret ?? ""}
            placeholder="开启加签时必填"
            onChange={(value) => setForm((current) => ({ ...current, secret: value }))}
          />
          <SwitchField
            id="webhook-enabled"
            label="开启通知"
            checked={Boolean(form.enabled)}
            onCheckedChange={(enabled) => setForm((current) => ({ ...current, enabled }))}
          />
          <div className="flex gap-2">
            <Button type="button" variant="outline" className="rounded-md" disabled={busy === "test-webhook"} onClick={onTest}>
              <Bell className="size-4" aria-hidden="true" />
              测试
            </Button>
            <Button type="submit" className="rounded-md" disabled={busy === "save-webhook"}>
              <Send className="size-4" aria-hidden="true" />
              保存
            </Button>
          </div>
        </div>
      </form>
      {webhookSettings.length ? (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-surface-subtle">
                <TableHead className="min-w-[100px]">类型</TableHead>
                <TableHead className="min-w-[320px]">Webhook 地址</TableHead>
                <TableHead className="min-w-[110px]">加签</TableHead>
                <TableHead className="min-w-[120px]">状态</TableHead>
                <TableHead className="min-w-[110px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {webhookSettings.map((item) => (
                <TableRow key={`${item.provider}:${item.webhook_url}`}>
                  <TableCell>{webhookProviderLabel(item.provider)}</TableCell>
                  <TableCell className="max-w-[520px] truncate font-mono text-xs">{item.webhook_url}</TableCell>
                  <TableCell>
                    <Badge className={item.has_secret ? "rounded bg-info-bg text-info hover:bg-info-bg" : "rounded bg-muted text-muted-foreground hover:bg-muted"}>
                      {item.has_secret ? "已加签" : "未加签"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={item.enabled ? "rounded bg-safe-bg text-safe hover:bg-safe-bg" : "rounded bg-muted text-muted-foreground hover:bg-muted"}>
                      {item.enabled ? "开启" : "关闭"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button type="button" variant="outline" size="sm" className="rounded-md text-risk hover:text-risk" onClick={() => onDelete(item)}>
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
        <div className="rounded border border-dashed p-6 text-center text-sm text-muted-foreground">暂无 Webhook 通知。</div>
      )}
    </SettingsBoxRow>
  )
}

function WebhookProviderSelect({
  value,
  onChange,
}: {
  value: WebhookProvider
  onChange: (value: WebhookProvider) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="webhook-provider">类型</Label>
      <select
        id="webhook-provider"
        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value as WebhookProvider)}
      >
        <option value="dingtalk">钉钉</option>
        <option value="feishu">飞书</option>
      </select>
    </div>
  )
}

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  placeholder?: string
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}

function SwitchField({
  id,
  label,
  checked,
  onCheckedChange,
}: {
  id: string
  label: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}) {
  return (
    <div className="flex h-9 items-center gap-2">
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
      <Label htmlFor={id} className="cursor-pointer font-normal">
        {label}
      </Label>
    </div>
  )
}

function getDefaultDomain() {
  if (typeof window === "undefined") return ""
  return window.location.origin === "null" ? "" : window.location.origin
}

function webhookProviderLabel(provider: WebhookProvider) {
  return provider === "feishu" ? "飞书" : "钉钉"
}

function webhookPlaceholder(provider: WebhookProvider) {
  if (provider === "feishu") return "https://open.feishu.cn/open-apis/bot/v2/hook/..."
  return "https://oapi.dingtalk.com/robot/send?access_token=..."
}

function isWebhookUrl(provider: WebhookProvider, webhookUrl: string) {
  try {
    const url = new URL(webhookUrl)
    if (provider === "feishu") {
      return url.protocol === "https:" && url.host === "open.feishu.cn" && url.pathname.startsWith("/open-apis/bot/v2/hook/")
    }
    return url.protocol === "https:" && url.host === "oapi.dingtalk.com"
  } catch {
    return false
  }
}
