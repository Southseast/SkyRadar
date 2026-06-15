import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { LeakageDetailPage } from "@/pages/LeakageDetailPage"
import { fetchLeakageCode, fetchLeakageInfo, patchLeakageDetail } from "@/lib/api/results"

vi.mock("@/lib/api/results", () => ({
  fetchLeakageCode: vi.fn(),
  fetchLeakageInfo: vi.fn(),
  patchLeakageDetail: vi.fn(),
}))

const mockedFetchLeakageInfo = vi.mocked(fetchLeakageInfo)
const mockedFetchLeakageCode = vi.mocked(fetchLeakageCode)
const mockedPatchLeakageDetail = vi.mocked(patchLeakageDetail)

describe("LeakageDetailPage", () => {
  beforeEach(() => {
    mockedFetchLeakageInfo.mockReset()
    mockedFetchLeakageCode.mockReset()
    mockedPatchLeakageDetail.mockReset()
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
      datetime: "2026-06-05T08:00:00Z",
    })
    mockedFetchLeakageCode.mockResolvedValue({
      code: "Y29uc3Qgc2VjcmV0ID0gJ3Rva2VuJw==",
      affect: [{ type: "token", value: "token" }],
    })
    mockedPatchLeakageDetail.mockResolvedValue({ message: "处理成功" })

    render(
      <MemoryRouter initialEntries={["/view/leakage/leakage-1"]}>
        <Routes>
          <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("acme/skyradar")).toBeInTheDocument()
    expect(screen.getByText("const secret = 'token'")).toBeInTheDocument()
    expect(screen.getAllByText("token")).toHaveLength(2)

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
})
