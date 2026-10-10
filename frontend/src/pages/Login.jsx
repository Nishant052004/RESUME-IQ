import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../store";
import { useToast } from "../components/Toast.jsx";
import OAuthSetupModal from "../components/OAuthSetupModal.jsx";

const emailValid = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

const GoogleMark = () => (
  <svg viewBox="0 0 48 48" width="18" height="18" aria-hidden="true">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
  </svg>
);

const GitHubMark = () => (
  <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
  </svg>
);

const OAUTH_ERRORS = {
  not_configured: (p) => `${p} sign-in isn't set up on this server yet. Add the ${p.toUpperCase()}_CLIENT_ID and SECRET to backend/.env — see the README's OAuth setup section.`,
  invalid_state: () => "That sign-in link expired or looks tampered with. Please try again.",
  missing_code: (p) => `${p} didn't return an authorization code. Please try again.`,
  provider_error: (p) => `Couldn't reach ${p} to finish sign-in. Please try again.`,
  no_email: (p) => `${p} didn't share an email address, which ResumeIQ needs to identify you.`,
  invalid_response: () => "Unexpected sign-in response. Please try again.",
};

export default function Login() {
  const { login, register } = useApp();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", confirm: "", fullName: "" });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);
  const [oauthReady, setOauthReady] = useState({ google: false, github: false });
  const [setupFor, setSetupFor] = useState(null);

  useEffect(() => {
    api.get("/api/auth/oauth/status").then(setOauthReady).catch(() => {});
  }, []);

  // Unconfigured providers open a guided setup dialog; configured ones start
  // the real OAuth redirect.
  const oauthClick = (provider) => (e) => {
    if (oauthReady[provider]) return; // full navigation to the backend
    e.preventDefault();
    setSetupFor(provider);
  };

  const oauthHref = (provider) =>
    `/api/auth/oauth/${provider}?origin=${encodeURIComponent(window.location.origin)}`;

  // Surface OAuth failures the backend redirected back with.
  useEffect(() => {
    const error = searchParams.get("oauth_error");
    if (!error) return;
    const provider = (searchParams.get("provider") || "").replace(/^\w/, (c) => c.toUpperCase());
    const message = (OAUTH_ERRORS[error] || (() => "Sign-in failed. Please try again."))(provider);
    toast(`${provider || "OAuth"} sign-in`, message, "error");
    searchParams.delete("oauth_error");
    searchParams.delete("provider");
    setSearchParams(searchParams, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setErrors((err) => ({ ...err, [key]: undefined }));
  };

  const validate = () => {
    const next = {};
    if (!emailValid(form.email)) next.email = "Enter a valid email address.";
    if (form.password.length < 6) next.password = "Password must be at least 6 characters.";
    if (mode === "signup") {
      if (!form.fullName.trim()) next.fullName = "Your name is required.";
      if (form.confirm !== form.password) next.confirm = "Passwords do not match.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setBusy(true);
    try {
      if (mode === "login") {
        await login(form.email, form.password, remember);
        toast("Welcome back", "Signed in successfully.", "success");
      } else {
        await register(form.email, form.password, form.fullName, remember);
        toast("Account created", "Welcome to ResumeIQ.", "success");
      }
    } catch (err) {
      toast(mode === "login" ? "Sign in failed" : "Sign up failed", err.message, "error");
      setBusy(false);
    }
  };

  const submitForgot = (e) => {
    e.preventDefault();
    if (!emailValid(form.email)) {
      setErrors({ email: "Enter a valid email address." });
      return;
    }
    setForgotSent(true);
  };

  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="hero-logo">Resume<span>IQ</span></div>
        <div className="hero-copy">
          <h2>Hire on evidence,<br />not keywords.</h2>
          <p>
            Upload a batch of resumes, paste a job description, and get a ranked,
            explainable shortlist in seconds — with PII redaction and bias-aware
            scoring built in.
          </p>
          <div className="hero-points">
            <div><span className="dot" /> Semantic matching — understands React.js ↔ React, FastAPI ↔ Python backend</div>
            <div><span className="dot" /> Every score ships with “why matched / what's missing” evidence</div>
            <div><span className="dot" /> Human-in-the-loop review with a full recruiter feedback loop</div>
          </div>
          <div className="hero-mock" aria-hidden="true">
            <div className="hero-mock-title">Shortlist · Senior Backend Engineer</div>
            {[
              { name: "Priya S.", score: 92, color: "var(--success)", role: "8.4 yrs · FastAPI, PostgreSQL, Docker" },
              { name: "Meera I.", score: 76, color: "var(--primary)", role: "5 yrs · PyTorch, NLP, Kubernetes" },
              { name: "Rahul G.", score: 41, color: "var(--warn)", role: "7 yrs · Java, Spring Boot" },
            ].map((row) => (
              <div className="hero-mock-row" key={row.name}>
                <span className="hero-mock-ring" style={{ background: `conic-gradient(${row.color} ${row.score * 3.6}deg, var(--border) 0)` }}><i>{row.score}</i></span>
                <span className="hero-mock-who"><b>{row.name}</b><small>{row.role}</small></span>
                <span className="hero-mock-check" style={{ color: row.color }}>✓</span>
              </div>
            ))}
          </div>
        </div>
        <div className="small" style={{ opacity: 0.7 }}>© 2026 ResumeIQ</div>
      </div>

      <div className="auth-panel">
        <div className="auth-card">
          {forgot ? (
            forgotSent ? (
              <div className="empty">
                <div className="big">📨</div>
                <h3>Check your inbox</h3>
                <p className="dim small">If an account exists for {form.email}, a password reset link is on its way.</p>
                <button className="btn btn-block" style={{ marginTop: 16 }} onClick={() => { setForgot(false); setForgotSent(false); }}>
                  Back to sign in
                </button>
              </div>
            ) : (
              <form onSubmit={submitForgot}>
                <h2>Reset your password</h2>
                <p className="dim small" style={{ margin: "4px 0 18px" }}>Enter your account email and we'll send a reset link.</p>
                <div className="field">
                  <label>Email</label>
                  <input type="email" value={form.email} onChange={set("email")} placeholder="you@company.com" autoFocus />
                  {errors.email && <div className="error">{errors.email}</div>}
                </div>
                <button className="btn btn-primary btn-block" type="submit">Send reset link</button>
                <div className="auth-alt">
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setForgot(false)}>Back to sign in</button>
                </div>
              </form>
            )
          ) : (
            <>
              <h2 style={{ marginBottom: 2 }}>{mode === "login" ? "Sign in to ResumeIQ" : "Create your account"}</h2>
              <p className="dim small" style={{ marginBottom: 18 }}>
                {mode === "login" ? "Welcome back — your shortlists are waiting." : "Start screening smarter in minutes."}
              </p>
              <div className="oauth-row" style={{ marginBottom: 18 }}>
                <a className={`oauth-btn ${oauthReady.google ? "" : "needs-setup"}`} href={oauthHref("google")} onClick={oauthClick("google")}>
                  <GoogleMark /> Google
                </a>
                <a className={`oauth-btn ${oauthReady.github ? "" : "needs-setup"}`} href={oauthHref("github")} onClick={oauthClick("github")}>
                  <GitHubMark /> GitHub
                </a>
              </div>
              <div className="oauth-divider">or use email</div>
              <div className="auth-tabs" role="tablist">
                <button className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setErrors({}); }} type="button">Login</button>
                <button className={mode === "signup" ? "active" : ""} onClick={() => { setMode("signup"); setErrors({}); }} type="button">Sign Up</button>
              </div>
              <form onSubmit={submit} noValidate>
                {mode === "signup" && (
                  <div className="field">
                    <label>Full name</label>
                    <input value={form.fullName} onChange={set("fullName")} placeholder="Jane Recruiter" />
                    {errors.fullName && <div className="error">{errors.fullName}</div>}
                  </div>
                )}
                <div className="field">
                  <label>Email</label>
                  <input type="email" value={form.email} onChange={set("email")} placeholder="you@company.com" autoComplete="email" />
                  {errors.email && <div className="error">{errors.email}</div>}
                </div>
                <div className="field">
                  <label>Password</label>
                  <div className="input-wrap">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={form.password}
                      onChange={set("password")}
                      placeholder="••••••••"
                      autoComplete={mode === "login" ? "current-password" : "new-password"}
                      style={{ paddingRight: 42 }}
                    />
                    <button type="button" className="peek" onClick={() => setShowPassword((s) => !s)} aria-label="Toggle password visibility">
                      {showPassword ? "🙈" : "👁"}
                    </button>
                  </div>
                  {errors.password && <div className="error">{errors.password}</div>}
                </div>
                {mode === "signup" && (
                  <div className="field">
                    <label>Confirm password</label>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={form.confirm}
                      onChange={set("confirm")}
                      placeholder="••••••••"
                    />
                    {errors.confirm && <div className="error">{errors.confirm}</div>}
                  </div>
                )}
                <div className="auth-row">
                  <label>
                    <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                    Remember me
                  </label>
                  <a href="#" onClick={(e) => { e.preventDefault(); setForgot(true); }}>Forgot password?</a>
                </div>
                <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
                  {busy ? <span className="spinner" style={{ width: 16, height: 16, borderTopWidth: 2 }} /> : mode === "login" ? "Sign in" : "Create account"}
                </button>
              </form>
              <div className="auth-alt">
                {mode === "login" ? "New to ResumeIQ? " : "Already have an account? "}
                <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === "login" ? "signup" : "login"); setErrors({}); }}>
                  {mode === "login" ? "Create an account" : "Sign in"}
                </a>
              </div>
            </>
          )}
          {setupFor && <OAuthSetupModal provider={setupFor} onClose={() => setSetupFor(null)} />}
        </div>
      </div>
    </div>
  );
}
