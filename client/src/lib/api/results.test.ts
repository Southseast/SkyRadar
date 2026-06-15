import type { AxiosResponse } from "axios"
import { afterEach, describe, expect, it, vi } from "vitest"

import { apiClient } from "@/lib/api/client"
import { endpoints } from "@/lib/api/endpoints"
import { fetchLeakageCode, fetchLeakages, fetchTrend } from "@/lib/api/results"

describe("results api adapter", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("serializes leakage filters as typed v1 query parameters", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        data: [],
        meta: { total: 0 },
      },
    } as AxiosResponse)

    await fetchLeakages({
      status: { security: 0, desc: { $exists: false } },
      tag: "corp",
      language: "Python",
      page_size: 20,
      page: 2,
    })

    expect(getSpy).toHaveBeenCalledWith(endpoints.leakages, {
      params: {
        security: 0,
        desc_exists: false,
        tag: "corp",
        language: "Python",
        page: 2,
        page_size: 20,
      },
    })
  })

  it("returns stable trend defaults when nested fields are missing", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        data: {
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
        data: {
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
        data: [
          {
            _id: "leakage-1",
            security: 0,
            ignore: 0,
          },
        ],
        meta: { total: 1 },
      },
    } as AxiosResponse)

    const response = await fetchLeakages({
      status: { security: 0 },
      page_size: 10,
      page: 1,
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
