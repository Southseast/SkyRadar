import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { LeakageDetailPage } from "@/pages/LeakageDetailPage"
import { fetchLeakageCode, fetchLeakageInfo, patchLeakageDetail, triggerLeakageAIAnalysis } from "@/lib/api/results"
import { fetchQueryRules } from "@/lib/api/settings"

vi.mock("@/lib/api/results", () => ({
  fetchLeakageCode: vi.fn(),
  fetchLeakageInfo: vi.fn(),
  patchLeakageDetail: vi.fn(),
  triggerLeakageAIAnalysis: vi.fn(),
}))

vi.mock("@/lib/api/settings", () => ({
  fetchQueryRules: vi.fn(),
}))

const mockedFetchLeakageInfo = vi.mocked(fetchLeakageInfo)
const mockedFetchLeakageCode = vi.mocked(fetchLeakageCode)
const mockedPatchLeakageDetail = vi.mocked(patchLeakageDetail)
const mockedTriggerLeakageAIAnalysis = vi.mocked(triggerLeakageAIAnalysis)
const mockedFetchQueryRules = vi.mocked(fetchQueryRules)

describe("LeakageDetailPage", () => {
  beforeEach(() => {
    mockedFetchLeakageInfo.mockReset()
    mockedFetchLeakageCode.mockReset()
    mockedPatchLeakageDetail.mockReset()
    mockedTriggerLeakageAIAnalysis.mockReset()
    mockedFetchQueryRules.mockReset()
    mockedFetchQueryRules.mockResolvedValue([])
    mockedTriggerLeakageAIAnalysis.mockResolvedValue({ message: "已提交分析" })
  })

  it("loads leakage detail, decodes code, and submits the compatible payload", async () => {
    mockedFetchLeakageInfo.mockResolvedValue({
      _id: "leakage-1",
      link: "https://github.com/acme/skyradar/blob/main/secret.py",
      project: "acme/skyradar",
      project_url: "https://github.com/acme/skyradar",
      language: "Python",
      username: "acme",
      filepath: "secret.py",
      filename: "secret.py",
      security: 0,
      ignore: 0,
      tag: "credential",
      desc: "待复核",
      discovered_at: "2026-06-05T09:00:00Z",
      discovered_timestamp: 1780650000,
      datetime: "2026-06-05T08:00:00Z",
    })
    mockedFetchLeakageCode.mockResolvedValue({
      code: "Y29uc3Qgc2VjcmV0ID0gJ3Rva2VuJw==",
      affect: [{ type: "token", value: "token" }],
    })
    mockedFetchQueryRules.mockResolvedValue([
      {
        _id: "rule-1",
        keyword: '"token"',
        tag: "credential",
        search_type: "code",
        enabled: true,
        analysis_enabled: false,
      },
    ])
    mockedPatchLeakageDetail.mockResolvedValue({ message: "处理成功" })

    render(
      <MemoryRouter initialEntries={["/view/leakage/leakage-1"]}>
        <Routes>
          <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("acme/skyradar")).toBeInTheDocument()
    expect(screen.getByText("发现时间")).toBeInTheDocument()
    expect(screen.getByText((_, element) => element?.tagName === "PRE" && element.textContent === "const secret = 'token'")).toBeInTheDocument()
    expect(screen.getAllByText("token")).toHaveLength(3)
    expect(screen.getAllByText("token")[0].tagName).toBe("MARK")

    await userEvent.click(screen.getByRole("button", { name: "确认" }))

    await waitFor(() => {
      expect(mockedPatchLeakageDetail).toHaveBeenCalledWith({
        id: "leakage-1",
        project: "acme/skyradar",
        security: 0,
        ignore: 0,
        desc: "待复核",
      })
    })
    expect(screen.getByText("处理成功")).toBeInTheDocument()
  })

  it("renders a decode failure for invalid base64 without crashing", async () => {
    mockedFetchLeakageInfo.mockResolvedValue({
      _id: "leakage-2",
      link: undefined,
      project: "未知仓库",
      project_url: undefined,
      language: null,
      username: "",
      filepath: "未知文件",
      filename: "未知文件",
      security: 0,
      ignore: 0,
      tag: "未标记",
      discovered_at: "2026-06-05T09:00:00Z",
      discovered_timestamp: 1780650000,
      datetime: undefined,
    } as never)
    mockedFetchLeakageCode.mockResolvedValue({
      code: "%",
      affect: [],
    })

    render(
      <MemoryRouter initialEntries={["/view/leakage/leakage-2"]}>
        <Routes>
          <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("代码内容解码失败。")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "快速排查" })).toBeDisabled()
  })

  it("renders the empty code fallback", async () => {
    mockedFetchLeakageInfo.mockResolvedValue({
      _id: "leakage-3",
      link: "https://github.com/acme/skyradar/blob/main/empty.py",
      project: "acme/skyradar",
      project_url: "https://github.com/acme/skyradar",
      language: "Python",
      username: "acme",
      filepath: "empty.py",
      filename: "empty.py",
      security: 1,
      ignore: 1,
      tag: "credential",
      discovered_at: "2026-06-05T09:00:00Z",
      discovered_timestamp: 1780650000,
      datetime: "2026-06-05T08:00:00Z",
    })
    mockedFetchLeakageCode.mockResolvedValue({
      code: "",
      affect: [],
    })

    render(
      <MemoryRouter initialEntries={["/view/leakage/leakage-3"]}>
        <Routes>
          <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("暂无代码内容。")).toBeInTheDocument()
  })

  it("summarizes long code by default and expands on demand", async () => {
    const longCode = Array.from({ length: 220 }, (_, index) =>
      index === 120 ? "const token = 'matched-secret'" : `const line${index} = ${index}`,
    ).join("\n")

    mockedFetchLeakageInfo.mockResolvedValue({
      _id: "leakage-4",
      link: "https://github.com/acme/skyradar/blob/main/long.py",
      project: "acme/skyradar",
      project_url: "https://github.com/acme/skyradar",
      language: "Python",
      username: "acme",
      filepath: "long.py",
      filename: "long.py",
      security: 0,
      ignore: 0,
      tag: "credential",
      discovered_at: "2026-06-05T09:00:00Z",
      discovered_timestamp: 1780650000,
      datetime: "2026-06-05T08:00:00Z",
    })
    mockedFetchLeakageCode.mockResolvedValue({
      code: btoa(longCode),
      affect: [{ type: "token", value: "matched-secret" }],
    })
    mockedFetchQueryRules.mockResolvedValue([
      {
        _id: "rule-1",
        keyword: '"matched-secret"',
        tag: "credential",
        search_type: "code",
        enabled: true,
        analysis_enabled: false,
      },
    ])

    render(
      <MemoryRouter initialEntries={["/view/leakage/leakage-4"]}>
        <Routes>
          <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText(/摘要内容，已省略/)).toBeInTheDocument()
    expect(screen.getByText((_, element) => element?.tagName === "PRE" && Boolean(element.textContent?.includes("matched-secret")))).toBeInTheDocument()
    expect(screen.queryByText((_, element) => element?.tagName === "PRE" && Boolean(element.textContent?.includes("const line0 = 0")))).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "显示完整内容" }))

    expect(screen.getByText(/完整内容，220 行/)).toBeInTheDocument()
    expect(screen.getByText((_, element) => element?.tagName === "PRE" && Boolean(element.textContent?.includes("const line0 = 0")))).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "收起为摘要" })).toBeInTheDocument()
  })

  it("shows AI analysis and can submit a rerun", async () => {
    mockedFetchLeakageInfo.mockResolvedValue({
      _id: "leakage-5",
      link: "https://github.com/acme/skyradar/blob/main/ai.py",
      project: "acme/skyradar",
      project_url: "https://github.com/acme/skyradar",
      language: "Python",
      username: "acme",
      filepath: "ai.py",
      filename: "ai.py",
      security: 0,
      ignore: 0,
      tag: "credential",
      discovered_at: "2026-06-05T09:00:00Z",
      discovered_timestamp: 1780650000,
      datetime: "2026-06-05T08:00:00Z",
      ai_analysis: {
        status: "success",
        risk_level: "high",
        summary: "疑似真实凭据泄露",
        evidence: ["包含 token 字段"],
        recommendation: "轮换凭据",
        false_positive_reason: "",
        model: "gpt-4o-mini",
        analyzed_at: "2026-06-05T09:10:00Z",
      },
    })
    mockedFetchLeakageCode.mockResolvedValue({
      code: "Y29uc3QgdG9rZW4gPSAnc2VjcmV0Jw==",
      affect: [{ type: "token", value: "secret" }],
    })

    render(
      <MemoryRouter initialEntries={["/view/leakage/leakage-5"]}>
        <Routes>
          <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("疑似真实凭据泄露")).toBeInTheDocument()
    expect(screen.getByText("高风险")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "重新分析" }))

    await waitFor(() => {
      expect(mockedTriggerLeakageAIAnalysis).toHaveBeenCalledWith("leakage-5")
    })
    expect(screen.getByText("等待分析")).toBeInTheDocument()
  })
})
