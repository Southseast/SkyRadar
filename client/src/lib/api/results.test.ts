import type { AxiosResponse } from "axios"
import { afterEach, describe, expect, it, vi } from "vitest"

import { apiClient } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import { fetchLeakageCode, fetchLeakages, fetchTrend } from "@/lib/api/results"

describe("results api adapter", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("serializes leakage status as the JSON query parameter", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        msg: "暂无数据",
        result: [],
        total: 0,
      },
    } as AxiosResponse)

    await fetchLeakages({
      status: { security: 0, desc: { $exists: false } },
      tag: "corp",
      language: "Python",
      limit: 20,
      from: 2,
    })

    expect(getSpy).toHaveBeenCalledWith(endpoints.leakage, {
      params: {
        status: JSON.stringify({ security: 0, desc: { $exists: false } }),
        tag: "corp",
        language: "Python",
        limit: 20,
        from: 2,
      },
    })
  })

  it("returns stable trend defaults when nested fields are missing", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        result: {
          today: {
            total: 7,
          },
        },
      },
    } as AxiosResponse)

    await expect(fetchTrend()).resolves.toEqual({
      all: {
        total: 0,
        ignore: 0,
        risk: 0,
      },
      today: {
        total: 7,
        ignore: 0,
        risk: 0,
      },
      engine: {
        status: false,
        last: 0,
      },
    })
  })

  it("normalizes affected asset shapes without dropping string assets", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        result: {
          code: "c2VjcmV0",
          affect: ["api.example.com", { type: "email", value: "security@example.com" }, null, { value: "10.0.0.1" }, { type: "ip" }],
        },
      },
    } as AxiosResponse)

    await expect(fetchLeakageCode("leakage-1")).resolves.toEqual({
      code: "c2VjcmV0",
      affect: [
        { type: "unknown", value: "api.example.com" },
        { type: "email", value: "security@example.com" },
        { type: "unknown", value: "10.0.0.1" },
      ],
    })
  })

  it("normalizes missing leakage fields from list records", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        result: [
          {
            _id: "leakage-1",
            security: 0,
            ignore: 0,
          },
        ],
        total: 1,
      },
    } as AxiosResponse)

    const response = await fetchLeakages({
      status: { security: 0 },
      limit: 10,
      from: 1,
    })

    expect(response.result[0]).toMatchObject({
      _id: "leakage-1",
      project: "未知仓库",
      filepath: "未知文件",
      filename: "未知文件",
      tag: "未标记",
    })
    expect(response.result[0].project_url).toBeUndefined()
    expect(response.result[0].link).toBeUndefined()
  })
})
