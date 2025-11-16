import { BrowserRouter as Router, Routes, Route, Navigate, useParams, useLocation } from "react-router-dom";
import DimensionsPage from "./components/DimensionsPage";
import DimensionAssessmentPage from "./components/DimensionAssessmentPage";
import DashboardPage from "./components/DashboardPage";
import SettingsPage from "./components/SettingsPage";
import Header from "./components/shared/Header";
import HelpPage from "./components/HelpPage";

export default function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

function AppShell() {
  const location = useLocation();
  const isAssessmentRoute = /^\/dimensions\/\d+\/assessment/.test(location.pathname);

  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <div className={`app-container${isAssessmentRoute ? " app-container--wide" : ""}`}>
          <Routes>
            <Route path="/" element={<DimensionsPage />} />
            <Route path="/dimensions/:dimensionId/assessment" element={<DimensionAssessmentPage />} />
            <Route path="/dimensions/:dimensionId/themes/*" element={<LegacyThemesRedirect />} />
            <Route path="/assessments" element={<div className="card"><h1 className="settings-heading">Assessments</h1><p className="settings-subcopy">Coming soon...</p></div>} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function LegacyThemesRedirect() {
  const { dimensionId } = useParams<{ dimensionId: string }>();
  if (!dimensionId) {
    return <Navigate to="/" replace />;
  }
  return <Navigate to={`/dimensions/${dimensionId}/assessment`} replace />;
}
