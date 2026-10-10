# ResumeIQ — Frontend UI Prototype

This documents the UI prototype added on top of the main project plan (see `README.md` for the full module/phase breakdown). It's a single-file, self-contained front-end (`resumeiq-ui.html`) demonstrating the full recruiter-facing experience, including a login/sign-up flow.

---

## 1. What Was Added

### Authentication Screens
- Email/password **Login** and **Sign Up** forms (toggle tabs on one card)
- Inline validation: email format check, minimum password length, confirm-password match on sign-up
- Show/hide password toggle
- "Remember me" checkbox — persists the session in the browser so a reload skips straight to the dashboard
- "Forgot password" flow (email entry → mock "reset link sent" confirmation)
- Google / GitHub sign-in buttons (visual placeholders for now)
- Loading state + success toast on login/signup, then a smooth transition into the dashboard

### Recruiter Dashboard
- **Overview** — stat cards (Total Candidates, Avg. Match Score, Shortlisted, Pending Review), a "Top Ranked Candidates" mini-list, and a recent-activity feed
- **Upload & JD** — job description textarea with a mock "Analyze" step that surfaces detected skill chips, plus a drag-and-drop resume upload zone with per-file parsing status
- **Candidates** — searchable, filterable (All / Shortlisted / Pending / Rejected), and sortable candidate list; each card shows match score, top skills, and status
- **Candidate detail modal** — the explainable-AI view: why the candidate matched, what's missing, a quoted evidence snippet, and Shortlist / Keep Reviewing / Reject actions with a recruiter-feedback dropdown (Relevant / Not relevant / Missing required skill)
- **Analytics** — skill-coverage bar chart, status-breakdown doughnut chart, and match-score distribution chart (via Chart.js)
- **Settings** — five scoring-weight sliders (Skills/Experience/Projects/Education/Certifications) that auto-balance to 100%, with a live weighted-score preview; a working **PII redaction toggle** that masks candidate emails/phone numbers everywhere in the UI; a bias-aware-screening indicator (always on); and a light/dark theme toggle

### General
- Fully responsive layout — sidebar collapses behind a hamburger menu on narrow screens
- Light/dark theme, remembered per browser
- Toast notifications for key actions (login, decisions, PII toggle, etc.)

---

## 2. File

| File | Description |
|---|---|
| `resumeiq-ui.html` | Single self-contained HTML/CSS/JS file — no build step, no dependencies to install. Open it directly in any modern browser. |

---

## 3. How This Maps to the Module Plan

Cross-referencing the modules from the main `README.md`:

| Module | Status in this prototype |
|---|---|
| Module 1 — Ingestion | Upload UI built; actual PDF/DOCX parsing not wired up (backend pending) |
| Module 4 — Scoring & Explainability | UI and interaction pattern built; scores/explanations are mock data |
| Module 5 — Privacy & Fairness | PII redaction **toggle works in the UI**; real detection/redaction logic still needs the backend |
| Module 6 — Dashboard | Fully built in this prototype |
| Module 7 — Human-in-the-Loop Review | Accept/Reject/Feedback flow works in the UI; decisions aren't persisted to a database yet |
| Module 8 — Auth, Infra & Deployment | Login/Sign-up UI built; real JWT/OAuth auth against a backend is still pending |

---

## 4. Known Limitations (by design, since there's no backend yet)

- **Authentication is simulated** — any syntactically valid email plus a 6+ character password logs a user in. There's no real account system, and no passwords are stored anywhere.
- **All data is mock** — candidates, resumes, and JD analysis results are hardcoded sample data and reset on reload (unless "Remember me" kept the session).
- **Charts need internet access** — Chart.js loads from a CDN, so the Analytics page needs connectivity to render.

---

## 5. Suggested Next Steps

1. Build Module 8's real FastAPI + JWT/OAuth backend and swap it in for the mocked login.
2. Wire Modules 1–5's API endpoints into this UI, replacing the mock arrays with live `fetch` calls.
3. Move scoring-weight and PII-redaction settings from local UI state into the backend, so they persist per recruiter/account.
4. Persist Human-in-the-Loop decisions (accept/reject/feedback) to the database instead of in-memory state.
