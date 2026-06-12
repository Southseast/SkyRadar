import { Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "@/components/layout/AppShell"
import { LeakageDetailPage } from "@/pages/LeakageDetailPage"
import { ResultsPage } from "@/pages/ResultsPage"
import { SettingsPage } from "@/pages/SettingsPage"

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<ResultsPage />} />
        <Route path="/view/leakage/:id" element={<LeakageDetailPage />} />
        <Route path="/setting/:tab" element={<SettingsPage />} />
        <Route path="/setting" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

export default App
