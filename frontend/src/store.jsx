import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearToken, getToken, setToken } from "./api";

const AppContext = createContext(null);

const THEME_KEY = "resumeiq_theme";
export const DEFAULT_WEIGHTS = {
  skills: 40,
  experience: 25,
  projects: 15,
  education: 10,
  certifications: 10,
};
const ACTIVE_JD_KEY = "resumeiq_active_jd";

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);
  const [theme, setThemeState] = useState(() => localStorage.getItem(THEME_KEY) || "light");
  const [settings, setSettings] = useState({ weights: { ...DEFAULT_WEIGHTS }, piiRedaction: true, theme: "light" });
  const [activeJdId, setActiveJdIdState] = useState(() => {
    const raw = localStorage.getItem(ACTIVE_JD_KEY);
    return raw ? Number(raw) : null;
  });

  const setTheme = useCallback((next) => {
    setThemeState(next);
    localStorage.setItem(THEME_KEY, next);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    (async () => {
      if (!getToken()) {
        setBooting(false);
        return;
      }
      try {
        const me = await api.get("/api/auth/me");
        setUser(me);
        const remote = await api.get("/api/settings");
        setSettings({
          weights: { ...DEFAULT_WEIGHTS, ...(remote.weights || {}) },
          piiRedaction: remote.pii_redaction,
          theme: remote.theme || "light",
        });
      } catch {
        clearToken();
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  const login = useCallback(async (email, password, remember) => {
    const data = await api.post("/api/auth/login", { email, password });
    setToken(data.access_token, remember);
    setUser(data);
    const remote = await api.get("/api/settings");
    setSettings({
      weights: { ...DEFAULT_WEIGHTS, ...(remote.weights || {}) },
      piiRedaction: remote.pii_redaction,
      theme: remote.theme || "light",
    });
    return data;
  }, []);

  const register = useCallback(async (email, password, fullName, remember) => {
    const data = await api.post("/api/auth/register", { email, password, full_name: fullName });
    setToken(data.access_token, remember);
    setUser(data);
    return data;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const saveSettings = useCallback(async (patch) => {
    const body = {
      weights: patch.weights ?? settings.weights,
      pii_redaction: patch.piiRedaction ?? settings.piiRedaction,
      theme: patch.theme ?? theme,
    };
    const remote = await api.put("/api/settings", body);
    setSettings({
      weights: { ...DEFAULT_WEIGHTS, ...(remote.weights || {}) },
      piiRedaction: remote.pii_redaction,
      theme: remote.theme || "light",
    });
    if (patch.theme) setTheme(patch.theme);
    return remote;
  }, [settings, theme, setTheme]);

  const setActiveJdId = useCallback((id) => {
    setActiveJdIdState(id);
    if (id == null) localStorage.removeItem(ACTIVE_JD_KEY);
    else localStorage.setItem(ACTIVE_JD_KEY, String(id));
  }, []);

  const value = useMemo(
    () => ({
      user, booting, login, register, logout,
      theme, setTheme,
      settings, saveSettings,
      activeJdId, setActiveJdId,
    }),
    [user, booting, login, register, logout, theme, setTheme, settings, saveSettings, activeJdId, setActiveJdId],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  return useContext(AppContext);
}
