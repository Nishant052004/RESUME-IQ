import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useApp } from "./store";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Overview from "./pages/Overview.jsx";
import Upload from "./pages/Upload.jsx";
import Candidates from "./pages/Candidates.jsx";
import Analytics from "./pages/Analytics.jsx";
import Settings from "./pages/Settings.jsx";
import OAuthCallback from "./components/OAuthCallback.jsx";

export default function App() {
  const { user, booting } = useApp();
  const location = useLocation();

  if (booting) {
    return (
      <div className="boot-screen">
        <div className="boot-logo">Resume<span>IQ</span></div>
        <div className="spinner" />
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/oauth/callback" element={<OAuthCallback />} />
        <Route path="*" element={<Navigate to="/login" replace state={location.pathname} />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/app" replace />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route path="/app" element={<Dashboard />}>
        <Route index element={<Overview />} />
        <Route path="upload" element={<Upload />} />
        <Route path="candidates" element={<Candidates />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}
