import { Navigate, Route, Routes } from "react-router-dom";
import { AnalysisPage } from "../pages/AnalysisPage";
import { DashboardPage } from "../pages/DashboardPage";
import { DatasetDiscoveryPage } from "../pages/DatasetDiscoveryPage";
import { GeneResearchPage } from "../pages/GeneResearchPage";
import { KnowledgePage } from "../pages/KnowledgePage";
import { LiteraturePage } from "../pages/LiteraturePage";
import { NewResearchPage } from "../pages/NewResearchPage";
import { PathwaysPage } from "../pages/PathwaysPage";
import { ReportsPage } from "../pages/ReportsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { VisualizationsPage } from "../pages/VisualizationsPage";
import { AppShell } from "./AppShell";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="research" element={<NewResearchPage />} />
        <Route path="datasets" element={<DatasetDiscoveryPage />} />
        <Route path="genes" element={<GeneResearchPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="pathways" element={<PathwaysPage />} />
        <Route path="visualizations" element={<VisualizationsPage />} />
        <Route path="literature" element={<LiteraturePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
