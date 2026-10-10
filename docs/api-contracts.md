# ResumeIQ API Contracts

Base URL: `http://localhost:8000`. All endpoints are JSON unless noted. Authenticated endpoints require `Authorization: Bearer <access_token>`.

Interactive reference: `/docs` (Swagger UI).

---

## Auth (Module 8)

### `POST /api/auth/register` → 201
```json
{ "email": "recruiter@corp.com", "password": "secret123", "full_name": "Jane Recruiter" }
```
Response: `{ "id", "email", "full_name", "access_token", "token_type": "bearer" }`
Errors: `409` email exists, `422` validation (password ≥ 6 chars, valid email).

### `POST /api/auth/login` → 200
Same body minus `full_name`. Response shape identical. Errors: `401` bad credentials.

### `GET /api/auth/me` → 200
Current user. Errors: `401` missing/invalid token.

---

## OAuth sign-in (Module 8)

### `GET /api/auth/oauth/status`
`{ "google": true, "github": false }` — which providers have credentials configured.

### `GET /api/auth/oauth/{provider}?origin=<spa-origin>` → 307
Redirects to Google/GitHub consent. `origin` must be allow-listed (CORS_ORIGINS or the API's own origin); it rides inside a signed, 10-minute JWT `state`. Unconfigured provider → 307 back to `/login?oauth_error=not_configured`.

### `GET /api/auth/oauth/{provider}/callback?code&state` → 302
Exchanges the code, fetches the profile, upserts the user by email (existing accounts are linked; OAuth accounts cannot password-login), then redirects to `<origin>/oauth/callback?token=<app JWT>`. Failure modes redirect to `/login?oauth_error=<reason>`: `invalid_state`, `missing_code`, `provider_error`, `no_email`, `not_configured`.

---

## Job Descriptions (Modules 1–2)

### `POST /api/jd` → 201
```json
{ "title": "Senior Backend Engineer", "company": "Acme", "text": "…full JD text (min 30 chars)…" }
```
Response includes the extracted profile:
```json
{
  "id": 1, "title": "…", "company": "…", "created_at": "…", "text_length": 842,
  "profile": {
    "title": "…", "must_have_skills": ["python", "fastapi"], "nice_to_have_skills": ["kubernetes"],
    "min_years_experience": 4, "education": [], "certifications": [],
    "responsibilities": ["…"], "skill_evidence": { "python": ["…quote…"] }
  }
}
```

### `GET /api/jd` → list · `GET /api/jd/{id}` → 200/404 · `DELETE /api/jd/{id}` → 204

---

## Resumes (Modules 1, 2, 5)

### `POST /api/resumes/upload` (multipart, field `files`, 1..n) → 200
Accepts PDF / DOCX / TXT / MD, ≤ 10 MB each. **Every file reports its own status**; one bad file never fails the batch.
```json
{ "uploaded": 2, "files": [
  { "filename": "a.pdf", "status": "parsed", "resume_id": 7, "candidate_name": "Priya Sharma",
    "skills_found": 14, "experience_years": 6.0 },
  { "filename": "broken.pdf", "status": "error", "error": "Could not extract text: …" } ] }
```
With PII redaction ON (default), text is redacted + protected-attribute-stripped **before** storage; raw resume text is never returned by any endpoint.

### `GET /api/resumes` → list of parsed profiles (no raw text) · `DELETE /api/resumes/{id}` → 204

---

## Matching, Results, Analytics, Export (Modules 3–4)

### `POST /api/jd/{jd_id}/match` → 200
Runs extract → match → score → rank over **all** of the user's resumes. Replaces previous results for that JD and carries recruiter decisions over per candidate.
Response: `{ "jd_id", "candidates_scored", "top_score" }`. Errors: `400` no resumes uploaded.

### `GET /api/jd/{jd_id}/results` → ranked candidates
```json
[{
  "result_id": 31, "resume_id": 7, "candidate_name": "Priya Sharma", "filename": "priya_sharma.txt",
  "rank": 1, "score": 75.0,
  "subscores": { "skills": 0.81, "experience": 1.0, "projects": 0.17 },
  "skills": ["python", "fastapi"], "certifications": ["AWS Certified …"], "experience_years": 8.4,
  "education": [{ "degree": "B.TECH", "field": "Computer Science", "institution": "IIT Delhi" }],
  "projects": [{ "title": "ML Resume Ranker" }],
  "matched": [{ "skill": "python", "tier": "must", "evidence": ["…quote…"] }],
  "missing": [{ "skill": "kubernetes", "tier": "must" }],
  "explanation": {
    "why_matched": ["8.4 years of experience meets the 4+ year requirement.", "Required skill — python: “…”"],
    "missing_required": ["generative ai"], "missing_nice_to_have": ["chromadb"],
    "evidence": ["…quotes…"], "criteria": ["Skills coverage — weight 50%", "Protected attributes … excluded"]
  },
  "weights_used": { "skills": 0.5, "experience": 0.31, "projects": 0.19 },
  "status": "shortlisted", "recruiter_feedback": "relevant", "recruiter_note": ""
}]
```

### `GET /api/jd/{jd_id}/analytics`
```json
{ "candidates": 5, "avg_score": 45.4,
  "status_breakdown": { "shortlisted": 1, "pending": 3, "rejected": 1 },
  "score_distribution": { "0-20": 1, "21-40": 1, "41-60": 2, "61-80": 1, "81-100": 0 },
  "skill_coverage": [{ "skill": "python", "covered": 4, "total": 5 }] }
```

### `GET /api/jd/{jd_id}/export` → `text/csv`
Columns: rank, candidate, match_score, experience_years, skills, missing_required, status, recruiter_feedback.

---

## Review (Module 7)

### `POST /api/results/{result_id}/decision` → 200
```json
{ "status": "shortlisted", "feedback": "relevant", "note": "Strong FastAPI depth" }
```
`status` ∈ `shortlisted | pending | rejected`; `feedback` ∈ `relevant | not_relevant | missing_required_skill | ""`.
Response returns the decision **and the untouched AI score** (`ai_score`). Errors: `404` unknown result.

### `GET /api/review/activity` → last 12 recruiter decisions with candidate, JD, AI score, timestamp.

---

## Settings

### `GET /api/settings` → `{ "weights": {}, "pii_redaction": true, "theme": "light" }`
### `PUT /api/settings`
Body (all optional): `{ "weights": { "skills": 50, "experience": 20, … }, "pii_redaction": false, "theme": "dark" }`.
Weights are normalized server-side; unknown keys are dropped. Weight changes apply on the **next** match run.

---

## Meta

### `GET /api/health` → `{ "status": "ok", "app": "ResumeIQ" }`
