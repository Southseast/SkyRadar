import { Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getStatusLabels, type ResultQueryState, type ResultStatusLabel } from "@/features/results/query"
import type { StatisticItem } from "@/types/api"

interface ResultsFiltersProps {
  state: ResultQueryState
  tagOptions: StatisticItem[]
  languageOptions: StatisticItem[]
  onChange: (state: ResultQueryState) => void
}

const emptyValue = "__all"

export function ResultsFilters({ state, tagOptions, languageOptions, onChange }: ResultsFiltersProps) {
  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
      <div className="space-y-1.5">
        <Label htmlFor="tag-filter">标签</Label>
        <Select
          value={state.tag || emptyValue}
          onValueChange={(value) => onChange({ ...state, page: 1, tag: value === emptyValue ? "" : value })}
        >
          <SelectTrigger id="tag-filter" className="w-full rounded-md">
            <SelectValue placeholder="全部标签" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={emptyValue}>全部标签</SelectItem>
            {tagOptions.filter((item) => item._id).map((item) => (
              <SelectItem key={item._id} value={String(item._id)}>
                {item._id} ({item.value})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="language-filter">语言</Label>
        <Select
          value={state.language || emptyValue}
          onValueChange={(value) => onChange({ ...state, page: 1, language: value === emptyValue ? "" : value })}
        >
          <SelectTrigger id="language-filter" className="w-full rounded-md">
            <SelectValue placeholder="全部语言" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={emptyValue}>全部语言</SelectItem>
            {languageOptions.filter((item) => item._id).map((item) => (
              <SelectItem key={item._id} value={String(item._id)}>
                {item._id} ({item.value})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="status-filter">状态</Label>
        <Select
          value={state.status}
          onValueChange={(value) => onChange({ ...state, page: 1, status: value as ResultStatusLabel })}
        >
          <SelectTrigger id="status-filter" className="w-full rounded-md">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            {getStatusLabels().map((label) => (
              <SelectItem key={label} value={label}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Button
        type="button"
        variant="outline"
        className="rounded-md"
        onClick={() => onChange({ page: 1, limit: state.limit, tag: "", language: "", status: "待审" })}
      >
        <Search className="size-4" aria-hidden="true" />
        重置
      </Button>
    </div>
  )
}
