import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../store";

const NAV = [
  { to: "/app", end: true, label: "Overview", icon: "M3 13h8V3H3v10zm10 8h8V11h-8v10zM3 21h8v-6H3v6zm10-14v6h8V7h-8z" },
  { to: "/app/upload", label: "Upload & JD", icon: "M12 16V4m0 0L7 9m5-5 5 5M4 20h16" },
  { to: "/app/candidates", label: "Candidates", icon: "M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0zm6 9a8 8 0 1 0-16 0" },
  { to: "/app/analytics", label: "Analytics", icon: "M4 20V10m6 10V4m6 16v-7m6 7V8" },
  { to: "/app/settings", label: "Settings", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7.5 7.5 0 0 0-2-1.2L14.5 3h-4L10 5.6a7.5 7.5 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7.5 7.5 0 0 0 2 1.2l.5 2.6h4l.5-2.6a7.5 7.5 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.07-.4.1-.8.1-1.2z" },
];

export default function Dashboard() {
  const { user, logout, theme, setTheme } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const current = NAV.find((n) => (n.end ? location.pathname === n.to : location.pathname.startsWith(n.to)));
  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");

  return (
    <div className="shell">
      {menuOpen && <div className="modal-backdrop" style={{ alignItems: "stretch", padding: 0 }} onClick={() => setMenuOpen(false)} />}
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">Resume<span>IQ</span></div>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            onClick={() => setMenuOpen(false)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d={item.icon} />
            </svg>
            {item.label}
          </NavLink>
        ))}
        <div className="sidebar-footer">
          <div className="user-chip">
            {user?.avatar_url ? (
              <img className="avatar" src={user.avatar_url} alt="" referrerPolicy="no-referrer" />
            ) : (
              <div className="avatar">{initials}</div>
            )}
            <div className="who">
              <b>{user?.full_name || "Recruiter"}</b>
              <span>{user?.email}</span>
            </div>
          </div>
          <div className="row">
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
            </button>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={() => { logout(); navigate("/login"); }}>
              Log out
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="row">
            <button className="btn btn-ghost btn-sm hamburger" onClick={() => setMenuOpen(true)} aria-label="Open menu">☰</button>
            <h1 style={{ margin: 0 }}>{current?.label || "Overview"}</h1>
          </div>
          <div className="topbar-actions small dim">AI-powered screening · bias-aware</div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
