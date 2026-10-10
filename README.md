# ResumeIQ — AI Resume Screener

An AI-powered resume screening and candidate ranking platform that matches resumes against job descriptions using semantic (embedding/TF-IDF-based) analysis instead of plain keyword search — with explainable scores, a recruiter dashboard, PII redaction, bias-aware ranking, and human-in-the-loop review.

**This repository is a working implementation of the module plan in `docs/PROJECT-PLAN.md`** (the original planning README). Every module (1–8) is implemented and tested; the pipeline runs fully offline with zero API keys, with optional LLM enhancement when a key is configured.

---

### Quick start

```bash
# 1. Backend (Python 3.11+, deps already in requirements.txt)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# 2. Frontend (Node 18+)
cd frontend
npm install
npm run dev                  # http://localhost:5173 (proxies /api to :8000)
```

Create your own account from the Sign Up tab, or continue with Google / GitHub (see **OAuth setup** below).

### Option B — single server (backend also serves the built SPA)

```bash
cd frontend && npm install && npm run build
cd ../backend && pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
# open http://localhost:8000
```

### Option C — Docker

```bash
docker compose up --build
# frontend on http://localhost:3000, API on http://localhost:8000
```

## OAuth setup (Google & GitHub sign-in)

The login page ships working Google and GitHub buttons. Until you register
app credentials they show a friendly "not configured" hint instead of breaking.

1. **Google** — [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → *Create OAuth client ID* (type: Web application). Add authorized redirect URI:
   `http://localhost:8000/api/auth/oauth/google/callback`
2. **GitHub** — [GitHub Developer settings → OAuth Apps](https://github.com/settings/developers) → *New OAuth App*. Authorization callback URL:
   `http://localhost:8000/api/auth/oauth/github/callback`
3. Put the credentials in `backend/.env` (see `.env.example`):
   ```
   GOOGLE_CLIENT_ID=…    GOOGLE_CLIENT_SECRET=…
   GITHUB_CLIENT_ID=…    GITHUB_CLIENT_SECRET=…
   ```
4. Save the file. The development server watches `.env` and reloads itself:
   ```
   python -m uvicorn app.main:app --reload --reload-include='*.env' --reload-include='.*'
   ```
   (Without `--reload`, restart the backend once.) The buttons go live automatically — accounts are linked by verified email, so an OAuth sign-in to an existing email joins that account.

> Hosting elsewhere? Register the same callback paths against your public domain — they follow `<backend-origin>/api/auth/oauth/<provider>/callback`.

---

## What's implemented

| Module | Status | Where |
|---|---|---|
| 1 — Resume & JD Ingestion | ✅ PDF (PyMuPDF) / DOCX / TXT extraction, batch upload with per-file status, JD paste + analysis | `backend/app/ingestion/` |
| 2 — Information Extraction | ✅ Skills (technical/soft/spoken) with alias + implication graph, experience (roles, durations, total years), education, certifications, quantified achievements; structured JSON profiles for resumes and JDs | `backend/app/extraction/` |
| 3 — Semantic Matching | ✅ Alias-normalized TF-IDF (1–2 grams) cosine similarity, related-term resolution (React.js ↔ React, Postgres ↔ PostgreSQL, K8s ↔ Kubernetes), requirement matching with quoted evidence, project relevance | `backend/app/matching/` |
| 4 — Scoring, Ranking & Explainability | ✅ Configurable weighted scoring (skills/experience/projects/education/certs), ranking, "why matched / what's missing / evidence / criteria" explanations | `backend/app/scoring/` |
| 5 — Privacy & Fairness | ✅ Regex PII detection & redaction (email, phone, address, DOB, government IDs) applied **before** storage, protected-attribute stripping, transparent scoring-criteria logging | `backend/app/privacy/` |
| 6 — Recruiter Dashboard | ✅ React + Vite SPA: overview stats, upload & JD analysis, searchable/filterable/sortable candidate list, explainable candidate modal, Chart.js analytics, settings | `frontend/src/` |
| 7 — Human-in-the-Loop Review | ✅ Shortlist / keep reviewing / reject + feedback capture (relevant / not relevant / missing required skill); decisions stored **separately** from AI scores and survive re-scores; CSV export | `backend/app/review/` |
| 8 — Auth, Infra & Deployment | ✅ JWT auth (register/login/me, bcrypt), per-user settings, Docker + docker-compose (Postgres option), env config | `backend/app/auth/` |

### Design decisions worth knowing

- **No API key required.** Matching runs on alias-normalized TF-IDF + a skill implication graph (deterministic, offline). Set `LLM_API_KEY` to enable optional LLM enhancement of extraction/explanations.
- **Privacy-first storage.** When PII redaction is on (default), resumes are redacted and stripped of protected attributes *before* they hit the database or any API response — there is no endpoint that returns raw resume text.
- **Human decisions are durable.** Re-running a match rebuilds result rows but carries recruiter decisions over per candidate; AI scores are never modified by decisions.
- **Fair weighting.** When a JD lists no degree/certification requirement, that category is excluded and its weight is redistributed — candidates aren't penalized or rewarded arbitrarily.

---

## Testing

52 tests cover every module, including a full API integration test (upload PDF/DOCX → match → decide → analytics → export), the complete OAuth flow (state signing, origin allow-listing, account linking, every error path — with provider network calls mocked offline) and adversarial cases (empty resumes, PII in mixed formats, weight-driven ranking flips).

```bash
cd backend
python -m pytest tests/ -v
```

Every phase of the project plan has a testing gate — run these before merging anything.

---

## Environment variables (`.env` in `backend/`, see `.env.example`)

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string (SQLite out of the box, Postgres in Docker) | `sqlite:///resumeiq.db` |
| `JWT_SECRET` | Token signing secret — **change in production** | `change-me-in-production` |
| `LLM_API_KEY` | Optional LLM enhancement (empty = offline mode) | *(empty)* |
| `LLM_MODEL` / `LLM_BASE_URL` | LLM provider/model | `gpt-4o-mini` / OpenAI |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth sign-in | *(empty = hint shown)* |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth sign-in | *(empty = hint shown)* |
| `CORS_ORIGINS` | Comma-separated allowed origins (also allow-lists OAuth redirect targets) | `http://localhost:5173,…` |

## Project layout

```
├── backend/
│   ├── app/
│   │   ├── ingestion/      # Module 1 — upload, PDF/DOCX extraction
│   │   ├── extraction/     # Module 2 — lexicon + profile engine
│   │   ├── matching/       # Module 3 — TF-IDF + requirement matching
│   │   ├── scoring/        # Module 4 — weighted scoring, explanations, results API
│   │   ├── privacy/        # Module 5 — PII redaction, bias filters
│   │   ├── review/         # Module 7 — decisions, activity, CSV export
│   │   ├── auth/           # Module 8 — JWT, password hashing
│   │   ├── models.py, database.py, config.py, main.py
│   ├── tests/              # 52 pytest cases
│   ├── samples/            # demo resumes + JD
│   └── requirements.txt
├── frontend/               # React 18 + Vite + Chart.js SPA
│   └── src/{components,pages}
├── docs/
│   ├── PROJECT-PLAN.md     # original module/phase plan
│   └── api-contracts.md    # endpoint reference
├── docker-compose.yml
└── .env.example
```

## API surface

See `docs/api-contracts.md` for the full contract. Highlights:

```
POST /api/auth/register | login      GET /api/auth/me
POST /api/jd                         GET/DELETE /api/jd[/{id}]
POST /api/resumes/upload             GET /api/resumes
POST /api/jd/{id}/match              GET /api/jd/{id}/results
GET  /api/jd/{id}/analytics          GET /api/jd/{id}/export (CSV)
POST /api/results/{id}/decision      GET /api/review/activity
GET/PUT /api/settings
```

Interactive docs: `http://localhost:8000/docs` (Swagger UI).

## Known limitations / next steps

- PDF text extraction needs text-based PDFs — scanned/image-only resumes need OCR (planned).
- Google/GitHub sign-in is fully implemented (`backend/app/auth/oauth.py`) — add your provider credentials to go live; accounts link by verified email.
- Deployment targets (AWS/Render/Railway) are prepared via Docker but not pushed anywhere yet.

## License

MIT — see `LICENSE`.
