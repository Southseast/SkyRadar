import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

type SettingsSubheadProps = {
  title: ReactNode
  description?: ReactNode
  className?: string
}

type SettingsBoxProps = {
  children: ReactNode
  className?: string
}

type SettingsBoxRowProps = SettingsBoxProps & {
  muted?: boolean
}

type SettingsRowTitleProps = {
  icon: LucideIcon
  children: ReactNode
  trailing?: ReactNode
}

export function SettingsSubhead({ title, description, className }: SettingsSubheadProps) {
  return (
    <div className={cn("border-b border-border pb-2", className)}>
      <h2 className="text-2xl leading-snug font-semibold">{title}</h2>
      {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
    </div>
  )
}

export function SettingsBox({ children, className }: SettingsBoxProps) {
  return <div className={cn("overflow-hidden rounded-md border border-border bg-background text-sm", className)}>{children}</div>
}

export function SettingsBoxRow({ children, className, muted = false }: SettingsBoxRowProps) {
  return (
    <div className={cn("border-b border-border p-4 last:border-b-0", muted && "bg-surface-subtle", className)}>
      {children}
    </div>
  )
}

export function SettingsRowTitle({ icon: Icon, children, trailing }: SettingsRowTitleProps) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
      <strong>{children}</strong>
      {trailing}
    </div>
  )
}
