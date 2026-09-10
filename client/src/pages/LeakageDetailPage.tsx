import { Brain, ExternalLink, Maximize2, Minimize2, RefreshCw, Search, Save } from "lucide-react"
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
import { fetchLeakageCode, fetchLeakageInfo, patchLeakageDetail, triggerLeakageAIAnalysis } from "@/lib/api/results"
import { fetchQueryRules } from "@/lib/api/settings"
import type { AffectedAsset, Leakage, LeakageDetailForm, QueryRule } from "@/types/api"

const initialForm: LeakageDetailForm = {
  id: "",
  project: "",
  security: 1,
  ignore: 1,
  desc: "",
}

const searchSyntaxWords = new Set(["AND", "OR", "NOT"])
const searchQualifierPattern = /^(repo|org|user|path|filename|extension|language|in|is|fork|size|symbol):/i
const maxHighlightTerms = 16
const codePreviewContextLines = 8
const codePreviewFallbackLines = 80
const codePreviewMaxFullLines = 140
const codePreviewMaxFullChars = 12000

export function LeakageDetailPage() {
  const { id } = useParams()
  const [leakage, setLeakage] = useState<Leakage | null>(null)
  const [code, setCode] = useState("")
  const [highlightTerms, setHighlightTerms] = useState<string[]>([])
  const [affect, setAffect] = useState<AffectedAsset[]>([])
  const [form, setForm] = useState<LeakageDetailForm>({ ...initialForm, id: id ?? "" })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
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
          setHighlightTerms([])
          setAffect([])
          setError("未找到对应泄露记录。")
          return
        }

        const rules = await fetchQueryRules().catch(() => [])

        if (!mounted) return

        setLeakage(info)
        setCode(codeInfo?.code ? decodeBase64Utf8(codeInfo.code) : "")
        setHighlightTerms(buildHighlightTerms(info, codeInfo?.affect ?? [], rules))
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
          setHighlightTerms([])
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

  async function handleAnalyze() {
    if (!id) return

    setAnalyzing(true)
    setError(null)
    setNotice(null)
    try {
      const response = await triggerLeakageAIAnalysis(id)
      setLeakage((current) => (current ? { ...current, ai_analysis: { status: "pending" } } : current))
      setNotice(response.message ?? "已提交分析")
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setAnalyzing(false)
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
              <CodePreview key={id ?? "code-preview"} code={code} highlightTerms={highlightTerms} />
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

      <SettingsBox>
        <SettingsBoxRow>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold">AI 简析</h2>
            <Button type="button" variant="outline" size="sm" className="rounded-md" disabled={analyzing} onClick={handleAnalyze}>
              {analyzing ? <RefreshCw className="size-4 animate-spin" aria-hidden="true" /> : <Brain className="size-4" aria-hidden="true" />}
              {analyzing ? "提交中" : "重新分析"}
            </Button>
          </div>
        </SettingsBoxRow>
        <SettingsBoxRow>
          <AIAnalysisPanel analysis={leakage?.ai_analysis} />
        </SettingsBoxRow>
      </SettingsBox>
    </div>
  )
}

function AIAnalysisPanel({ analysis }: { analysis: Leakage["ai_analysis"] }) {
  if (!analysis?.status) {
    return <div className="text-sm text-muted-foreground">暂无 AI 分析。</div>
  }

  if (analysis.status !== "success") {
    const label: Record<string, string> = {
      pending: "等待分析",
      running: "分析中",
      failed: "分析失败",
      skipped: "已跳过",
    }
    return (
      <div className="space-y-2 text-sm">
        <Badge variant="outline" className="rounded">
          {label[analysis.status] ?? analysis.status}
        </Badge>
        {analysis.error ? <p className="text-risk">{analysis.error}</p> : null}
      </div>
    )
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={analysis.risk_level === "high" ? "rounded bg-risk-bg text-risk hover:bg-risk-bg" : "rounded bg-info-bg text-info hover:bg-info-bg"}>
          {analysis.risk_level === "high" ? "高风险" : analysis.risk_level === "medium" ? "中风险" : analysis.risk_level === "low" ? "低风险" : "未知风险"}
        </Badge>
        {analysis.model ? <span className="text-xs text-muted-foreground">{analysis.model}</span> : null}
        {analysis.analyzed_at ? <span className="text-xs text-muted-foreground">{formatDateTime(analysis.analyzed_at)}</span> : null}
      </div>
      {analysis.summary ? <p>{analysis.summary}</p> : null}
      {analysis.evidence?.length ? (
        <div>
          <div className="font-medium">证据点</div>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-muted-foreground">
            {analysis.evidence.map((item, index) => (
              <li key={`${item}-${index}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {analysis.recommendation ? (
        <div>
          <div className="font-medium">建议处置</div>
          <p className="mt-1 text-muted-foreground">{analysis.recommendation}</p>
        </div>
      ) : null}
      {analysis.false_positive_reason ? (
        <div>
          <div className="font-medium">可能误报原因</div>
          <p className="mt-1 text-muted-foreground">{analysis.false_positive_reason}</p>
        </div>
      ) : null}
    </div>
  )
}

function CodePreview({ code, highlightTerms }: { code: string; highlightTerms: string[] }) {
  const [showFullCode, setShowFullCode] = useState(false)

  const preview = buildCodePreview(code, highlightTerms)
  const displayedCode = showFullCode || !preview.truncated ? code : preview.text
  const lineCount = code ? code.split("\n").length : 0
  const canToggle = Boolean(code && preview.truncated)

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {code
            ? showFullCode || !preview.truncated
              ? `完整内容，${lineCount} 行`
              : `摘要内容，已省略 ${preview.omittedLineCount} 行`
            : "暂无代码内容"}
        </span>
        {canToggle ? (
          <Button type="button" variant="outline" size="sm" className="rounded-md" onClick={() => setShowFullCode((current) => !current)}>
            {showFullCode ? <Minimize2 className="size-4" aria-hidden="true" /> : <Maximize2 className="size-4" aria-hidden="true" />}
            {showFullCode ? "收起为摘要" : "显示完整内容"}
          </Button>
        ) : null}
      </div>
      <pre className="max-h-[560px] min-h-[320px] overflow-auto rounded-md border bg-surface-subtle p-3 font-mono text-xs leading-5 text-foreground">
        {displayedCode ? <HighlightedCode code={displayedCode} terms={highlightTerms} /> : "暂无代码内容。"}
      </pre>
    </div>
  )
}

function HighlightedCode({ code, terms }: { code: string; terms: string[] }) {
  const parts = splitByHighlightTerms(code, terms)

  return (
    <>
      {parts.map((part, index) =>
        part.highlight ? (
          <mark
            key={`${part.text}-${index}`}
            className="rounded-sm bg-warning-bg px-0.5 font-semibold text-foreground ring-1 ring-warning/30"
          >
            {part.text}
          </mark>
        ) : (
          <span key={`${part.text}-${index}`}>{part.text}</span>
        ),
      )}
    </>
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
      <SummaryRow label="发现时间">{formatDateTime(leakage.discovered_at)}</SummaryRow>
      <SummaryRow label="更新时间">{formatDateTime(leakage.datetime)}</SummaryRow>
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

function buildHighlightTerms(leakage: Leakage, affectedAssets: AffectedAsset[], rules: QueryRule[]) {
  const matchedRule = rules.find((rule) => rule.tag === leakage.tag)
  const terms = [
    ...extractSearchTerms(matchedRule?.keyword ?? ""),
    ...extractSearchTerms(leakage.tag),
    ...affectedAssets.flatMap((asset) => extractSearchTerms(asset.value)),
  ]

  return uniqueTerms(terms).slice(0, maxHighlightTerms)
}

function extractSearchTerms(value: string) {
  if (!value) return []

  const terms: string[] = []
  const quotedPattern = /"([^"]+)"|'([^']+)'/g
  const withoutQuoted = value.replace(quotedPattern, (_match, doubleQuoted: string | undefined, singleQuoted: string | undefined) => {
    terms.push(doubleQuoted ?? singleQuoted ?? "")
    return " "
  })

  for (const token of withoutQuoted.split(/[\s()[\]{}]+/)) {
    const cleaned = token.trim().replace(/^[,;]+|[,;]+$/g, "")
    if (!cleaned || searchSyntaxWords.has(cleaned.toUpperCase()) || searchQualifierPattern.test(cleaned)) continue
    terms.push(cleaned)
  }

  return terms.flatMap(splitCompoundTerm).filter(isHighlightTerm)
}

function splitCompoundTerm(term: string) {
  const parts = term.split(/[|,]+/).flatMap((part) => part.split(/[-_/]+/))
  return [term, ...parts]
}

function isHighlightTerm(term: string) {
  const normalized = term.trim()
  return normalized.length >= 3 && !searchSyntaxWords.has(normalized.toUpperCase()) && !searchQualifierPattern.test(normalized)
}

function uniqueTerms(terms: string[]) {
  const seen = new Set<string>()
  return terms
    .map((term) => term.trim())
    .filter((term) => {
      const key = term.toLocaleLowerCase()
      if (!term || seen.has(key)) return false
      seen.add(key)
      return true
    })
    .sort((left, right) => right.length - left.length)
}

function splitByHighlightTerms(text: string, terms: string[]) {
  if (!terms.length) return [{ text, highlight: false }]

  const pattern = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "gi")
  const parts: Array<{ text: string; highlight: boolean }> = []
  let lastIndex = 0

  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0
    if (index > lastIndex) {
      parts.push({ text: text.slice(lastIndex, index), highlight: false })
    }
    parts.push({ text: match[0], highlight: true })
    lastIndex = index + match[0].length
  }

  if (lastIndex < text.length) {
    parts.push({ text: text.slice(lastIndex), highlight: false })
  }

  return parts.length ? parts : [{ text, highlight: false }]
}

function buildCodePreview(code: string, terms: string[]) {
  if (!code) {
    return { text: "", truncated: false, omittedLineCount: 0 }
  }

  const lines = code.split("\n")
  if (lines.length <= codePreviewMaxFullLines && code.length <= codePreviewMaxFullChars) {
    return { text: code, truncated: false, omittedLineCount: 0 }
  }

  const matchedLineIndexes = findMatchedLineIndexes(lines, terms)
  const ranges = matchedLineIndexes.length
    ? mergeLineRanges(
        matchedLineIndexes.map((lineIndex) => ({
          start: Math.max(0, lineIndex - codePreviewContextLines),
          end: Math.min(lines.length - 1, lineIndex + codePreviewContextLines),
        })),
      )
    : [{ start: 0, end: Math.min(lines.length - 1, codePreviewFallbackLines - 1) }]

  const selectedLineCount = ranges.reduce((total, range) => total + range.end - range.start + 1, 0)
  const excerptLines: string[] = []
  let previousEnd = -1

  for (const range of ranges) {
    if (range.start > previousEnd + 1) {
      const omitted = range.start - previousEnd - 1
      excerptLines.push(`... 已省略 ${omitted} 行 ...`)
    }
    excerptLines.push(...lines.slice(range.start, range.end + 1))
    previousEnd = range.end
  }

  if (previousEnd < lines.length - 1) {
    excerptLines.push(`... 已省略 ${lines.length - previousEnd - 1} 行 ...`)
  }

  return {
    text: excerptLines.join("\n"),
    truncated: true,
    omittedLineCount: Math.max(0, lines.length - selectedLineCount),
  }
}

function findMatchedLineIndexes(lines: string[], terms: string[]) {
  const normalizedTerms = uniqueTerms(terms).map((term) => term.toLocaleLowerCase())
  if (!normalizedTerms.length) return []

  const matchedLineIndexes: number[] = []
  lines.forEach((line, index) => {
    const normalizedLine = line.toLocaleLowerCase()
    if (normalizedTerms.some((term) => normalizedLine.includes(term))) {
      matchedLineIndexes.push(index)
    }
  })
  return matchedLineIndexes
}

function mergeLineRanges(ranges: Array<{ start: number; end: number }>) {
  const sortedRanges = [...ranges].sort((left, right) => left.start - right.start)
  const mergedRanges: Array<{ start: number; end: number }> = []

  for (const range of sortedRanges) {
    const previous = mergedRanges[mergedRanges.length - 1]
    if (!previous || range.start > previous.end + 1) {
      mergedRanges.push({ ...range })
      continue
    }
    previous.end = Math.max(previous.end, range.end)
  }

  return mergedRanges
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
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
