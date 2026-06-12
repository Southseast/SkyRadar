import { Activity, Settings, ShieldAlert } from "lucide-react"
import type { ReactNode } from "react"
import { NavLink } from "react-router-dom"

import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "项目发现", icon: ShieldAlert },
  { to: "/setting#github", label: "设置", icon: Settings },
]

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b bg-card">
        <div className="mx-auto flex min-h-14 max-w-[1440px] items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex size-8 items-center justify-center rounded-md border bg-surface-subtle">
              <Activity className="size-4 text-info" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">SkyRadar</span>
              </div>
              <p className="text-xs text-muted-foreground">GitHub 开源项目发现</p>
            </div>
          </div>

          <nav aria-label="主导航" className="flex items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                aria-label={item.label}
                className={({ isActive }) =>
                  cn(
                    "inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm text-muted-foreground hover:bg-hover-surface hover:text-foreground",
                    isActive && "bg-selected-surface font-medium text-foreground",
                  )
                }
              >
                <item.icon className="size-4" aria-hidden="true" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-[1440px] px-4 py-4 sm:px-6 lg:py-5">
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  )
}
