import { ExternalLink, Search, Save } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { formatDateTime } from "@/features/results/format"
import { SettingsBox, SettingsBoxRow } from "@/features/settings/SettingsSection"
import { getErrorMessage } from "@/lib/api/client"
import { fetchLeakageCode, fetchLeakageInfo, patchLeakageDetail } from "@/lib/api/results"
import type { AffectedAsset, Leakage, LeakageDetailForm } from "@/types/api"

const initialForm: LeakageDetailForm = {
  id: "",
  project: "",
  security: 1,
  ignore: 1,
  desc: "",
}

export function LeakageDetailPage() {
  const { id } = useParams()
  const [leakage, setLeakage] = useState<Leakage | null>(null)
  const [code, setCode] = useState("")
  const [affect, setAffect] = useState<AffectedAsset[]>([])
  const [form, setForm] = useState<LeakageDetailForm>({ ...initialForm, id: id ?? "" })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadDetail() {
      if (!id) {
        setError("缺少泄露记录 ID。")
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)
      setNotice(null)

      try {
        const [info, codeInfo] = await Promise.all([fetchLeakageInfo(id), fetchLeakageCode(id)])

        if (!mounted) return

        if (!info) {
          setLeakage(null)
          setCode("")
          setAffect([])
          setError("未找到对应泄露记录。")
          return
        }

        setLeakage(info)
        setCode(codeInfo?.code ? decodeBase64Utf8(codeInfo.code) : "")
        setAffect(codeInfo?.affect ?? [])
        setForm({
          id,
          project: info.project,
          security: info.security ?? 1,
          ignore: info.ignore ?? 1,
          desc: info.desc ?? "",
        })
      } catch (requestError) {
        if (mounted) {
          setLeakage(null)
          setCode("")
          setAffect([])
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void loadDetail()

    return () => {
      mounted = false
    }
  }, [id])

  async function handleSubmit() {
    if (!id) return

    setSaving(true)
    setError(null)
    setNotice(null)

    try {
      const response = await patchLeakageDetail(form)
      setNotice(response.message ?? "处理成功")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  const quickCheckUrl = leakage?.project_url
    ? `${leakage.project_url}/search?utf8=%E2%9C%93&q=pass%20OR%20password%20OR%20passwd%20OR%20pwd%20OR%20smtp%20OR%20database`
    : ""

  return (
    <div className="space-y-4">
      <section className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">泄露详情</h1>
          <p className="mt-1 text-sm text-muted-foreground">查看代码片段、受影响资产并处理风险状态。</p>
        </div>
        {notice ? <div className="rounded border border-safe/20 bg-safe-bg px-3 py-1.5 text-sm text-safe">{notice}</div> : null}
      </section>

      {error ? (
        <Alert variant="destructive" className="rounded-md">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <SettingsBox>
          <SettingsBoxRow>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold">可疑文件</h2>
              <Badge variant="outline" className="rounded">
                {leakage?.tag ?? id ?? "未选择"}
              </Badge>
            </div>
          </SettingsBoxRow>
          <SettingsBoxRow>
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-5 w-64 rounded" />
                <Skeleton className="h-[320px] rounded" />
              </div>
            ) : (
              <pre className="min-h-[320px] overflow-auto rounded-md border bg-surface-subtle p-3 font-mono text-xs leading-5 text-foreground">
                {code || "暂无代码内容。"}
              </pre>
            )}
          </SettingsBoxRow>
        </SettingsBox>

        <div className="space-y-4">
          <SettingsBox>
            <SettingsBoxRow>
              <h2 className="text-base font-semibold">记录信息</h2>
            </SettingsBoxRow>
            <SettingsBoxRow className="space-y-3 text-sm">
              {loading ? <DetailSkeleton /> : <LeakageSummary leakage={leakage} />}
            </SettingsBoxRow>
          </SettingsBox>

          <SettingsBox>
            <SettingsBoxRow>
              <h2 className="text-base font-semibold">处理</h2>
            </SettingsBoxRow>
            <SettingsBoxRow className="space-y-4">
              <div className="space-y-2">
                <Label>是否安全</Label>
                <RadioGroup
                  value={String(form.security)}
                  onValueChange={(value) => setForm((current) => ({ ...current, security: Number(value) as 0 | 1 }))}
                >
                  <RadioOption id="security-safe" value="1" label="安全" />
                  <RadioOption id="security-risk" value="0" label="涉密" />
                </RadioGroup>
              </div>

              <div className="space-y-2">
                <Label>忽略仓库</Label>
                <RadioGroup
                  value={String(form.ignore)}
                  onValueChange={(value) => setForm((current) => ({ ...current, ignore: Number(value) as 0 | 1 }))}
                >
                  <RadioOption id="ignore-yes" value="1" label="忽略" />
                  <RadioOption id="ignore-no" value="0" label="监控" />
                </RadioGroup>
              </div>

              <div>
                <Label htmlFor="detail-note">备注</Label>
                <Textarea
                  id="detail-note"
                  className="mt-2 min-h-24"
                  placeholder="记录排查结论"
                  value={form.desc}
                  onChange={(event) => setForm((current) => ({ ...current, desc: event.target.value }))}
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <Button type="button" className="rounded-md" disabled={saving || loading || !leakage} onClick={handleSubmit}>
                  <Save className="size-4" aria-hidden="true" />
                  {saving ? "保存中" : "确认"}
                </Button>
                <Button type="button" variant="outline" className="rounded-md" disabled={!quickCheckUrl} asChild={Boolean(quickCheckUrl)}>
                  {quickCheckUrl ? (
                    <a href={quickCheckUrl} target="_blank" rel="noreferrer noopener">
                      <Search className="size-4" aria-hidden="true" />
                      快速排查
                    </a>
                  ) : (
                    <>
                      <Search className="size-4" aria-hidden="true" />
                      快速排查
                    </>
                  )}
                </Button>
              </div>
            </SettingsBoxRow>
          </SettingsBox>
        </div>
      </div>

      <SettingsBox>
        <SettingsBoxRow>
          <h2 className="text-base font-semibold">受影响资产 ({affect.length} 个)</h2>
        </SettingsBoxRow>
        <SettingsBoxRow className={affect.length && !loading ? "p-0" : undefined}>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-9 rounded" />
              <Skeleton className="h-9 rounded" />
            </div>
          ) : affect.length ? (
            <AffectedAssetsList assets={affect} />
          ) : (
            <div className="text-sm text-muted-foreground">暂无受影响资产。</div>
          )}
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}

function AffectedAssetsList({ assets }: { assets: AffectedAsset[] }) {
  return (
    <div className="divide-y divide-border">
      <div className="grid gap-3 bg-surface-subtle px-4 py-2 text-xs font-semibold text-muted-foreground sm:grid-cols-[10rem_minmax(0,1fr)]">
        <div>泄露类型</div>
        <div>受影响资产</div>
      </div>
      {assets.map((item, index) => (
        <div
          key={`${item.type}-${item.value}-${index}`}
          className="grid gap-2 px-4 py-3 text-sm transition-colors hover:bg-hover-surface/60 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-3"
        >
          <div className="font-medium">{item.type || "未知"}</div>
          <div className="min-w-0 break-all font-mono text-xs text-foreground">{item.value || "未知资产"}</div>
        </div>
      ))}
    </div>
  )
}

function LeakageSummary({ leakage }: { leakage: Leakage | null }) {
  if (!leakage) {
    return <div className="text-muted-foreground">暂无记录信息。</div>
  }

  const projectUrl = leakage.project_url || undefined
  const fileUrl = leakage.link || undefined

  return (
    <div className="space-y-3">
      <SummaryRow label="仓库">
        {projectUrl ? (
          <a className="inline-flex items-center gap-1 text-info hover:underline" href={projectUrl} target="_blank" rel="noreferrer noopener">
            {leakage.project}
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
        ) : (
          <span>{leakage.project}</span>
        )}
      </SummaryRow>
      <SummaryRow label="文件">
        {fileUrl ? (
          <a className="inline-flex max-w-full items-center gap-1 text-info hover:underline" href={fileUrl} target="_blank" rel="noreferrer noopener">
            <span className="truncate">{leakage.filename || leakage.filepath}</span>
            <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
          </a>
        ) : (
          <span>{leakage.filename || leakage.filepath}</span>
        )}
      </SummaryRow>
      <SummaryRow label="语言">{leakage.language || "未知"}</SummaryRow>
      <SummaryRow label="上传时间">{formatDateTime(leakage.datetime)}</SummaryRow>
      <SummaryRow label="命中标签">
        <Link to={`/?tag=${encodeURIComponent(leakage.tag)}`}>
          <Badge variant="outline" className="rounded">
            {leakage.tag}
          </Badge>
        </Link>
      </SummaryRow>
    </div>
  )
}

function SummaryRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="min-w-0 text-sm">{children}</div>
    </div>
  )
}

function RadioOption({ id, value, label }: { id: string; value: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <RadioGroupItem id={id} value={value} />
      <Label htmlFor={id} className="font-normal">
        {label}
      </Label>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-4 w-44 rounded" />
      <Skeleton className="h-4 w-56 rounded" />
      <Skeleton className="h-4 w-32 rounded" />
      <Skeleton className="h-4 w-40 rounded" />
    </div>
  )
}

function decodeBase64Utf8(value: string) {
  try {
    const binary = window.atob(value)
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
    return new TextDecoder().decode(bytes)
  } catch {
    return "代码内容解码失败。"
  }
}
