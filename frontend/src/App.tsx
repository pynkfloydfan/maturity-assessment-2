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
      <div className="min-h-screen bg-[#f7f9fc] text-[#121417]">
        <Header />
        <main className="min-h-[calc(100vh-80px)]">
          <Routes>
            <Route path="/" element={<DimensionsPage />} />
            <Route path="/dimensions/:dimensionId/themes" element={<ThemesPage />} />
            <Route path="/dimensions/:dimensionId/themes/:themeId/topics" element={<TopicsPage />} />
            <Route path="/dimensions/:dimensionId/themes/:themeId/topics/:topicId/assess" element={<AssessmentPage />} />
            <Route path="/assessments" element={<div className="p-8 text-center"><h1>Assessments</h1><p>Coming soon...</p></div>} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/help" element={<div className="p-8 text-center"><h1>Help</h1><p>Coming soon...</p></div>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
