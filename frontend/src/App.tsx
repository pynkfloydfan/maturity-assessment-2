import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import DimensionsPage from "./components/DimensionsPage";
import ThemesPage from "./components/ThemesPage";
import TopicsPage from "./components/TopicsPage";
import AssessmentPage from "./components/AssessmentPage";
import DashboardPage from "./components/DashboardPage";
import SettingsPage from "./components/SettingsPage";
import Header from "./components/shared/Header";

export default function App() {
  return (
    <Router>
      <div className="app-shell">
        <Header />
        <main className="app-main">
          <div className="app-container">
            <Routes>
              <Route path="/" element={<DimensionsPage />} />
              <Route path="/dimensions/:dimensionId/themes" element={<ThemesPage />} />
              <Route path="/dimensions/:dimensionId/themes/:themeId/topics" element={<TopicsPage />} />
              <Route path="/dimensions/:dimensionId/themes/:themeId/topics/:topicId/assess" element={<AssessmentPage />} />
              <Route path="/assessments" element={<div className="card"><h1 className="settings-heading">Assessments</h1><p className="settings-subcopy">Coming soon...</p></div>} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/help" element={<div className="card"><h1 className="settings-heading">Help</h1><p className="settings-subcopy">Coming soon...</p></div>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}
