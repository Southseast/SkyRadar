import { describe, expect, it } from "vitest"

import { parseResultQuery, resultStatusToApiStatus, toSearchParams } from "@/features/results/query"

describe("result query helpers", () => {
  it("uses pending review as the default status", () => {
    const state = parseResultQuery(new URLSearchParams())

    expect(state).toEqual({
      page: 1,
      limit: 10,
      tag: "",
      language: "",
      status: "待审",
    })
    expect(resultStatusToApiStatus(state.status)).toEqual({
      security: 0,
      reviewed: false,
    })
  })

  it("maps status labels to the API filter shape", () => {
    expect(resultStatusToApiStatus("不限")).toEqual({})
    expect(resultStatusToApiStatus("确认")).toEqual({ security: 0, reviewed: true })
    expect(resultStatusToApiStatus("误报")).toEqual({ security: 1 })
  })

  it("serializes URL state without noisy defaults", () => {
    const params = toSearchParams({
      page: 2,
      limit: 20,
      tag: "corp",
      language: "Python",
      status: "确认",
    })

    expect(params.toString()).toBe("page=2&limit=20&tag=corp&language=Python&status=%E7%A1%AE%E8%AE%A4")
  })
})
