# AI Resume Screener

An AI-powered resume screening and candidate ranking platform that matches resumes against job descriptions using semantic (LLM/embedding-based) analysis instead of plain keyword search — with explainable scores, a recruiter dashboard, bias-aware ranking, and human-in-the-loop review.

---

## 1. Project Objective

Build a system where a recruiter can:

1. Upload a job description and a batch of resumes (PDF/DOCX).
2. Get each resume automatically parsed, analyzed, and semantically matched against the JD.
3. See a ranked, explainable shortlist with clear "why matched / what's missing" reasoning.
4. Review, override, and export the final shortlist — with PII protection and bias-aware scoring built in.

**High-level flow:**

```
Resume Upload → Parser → AI Analyzer → Job Matching → Explainable Score → Human Review → Dashboard
```

---

## 2. Feature Set

### Core Features
- Resume upload (PDF/DOCX), multi-resume batch support, automatic text extraction
- Job description upload/paste with extraction of skills, qualifications, experience, keywords
- AI resume–JD matching score using semantic similarity (not just keyword overlap)
- Candidate ranking with configurable criteria + comparison table
- Skill extraction: technical skills, soft skills, tools, languages, certifications
- Experience analysis: companies, roles, projects, duration, relevant-experience calculation
- Education & certification extraction
- Resume strength/gap analysis with concrete improvement suggestions

### Advanced AI Features
- LLM-based contextual understanding (e.g., "developed REST APIs using FastAPI" → backend/API experience)
- Semantic skill matching across related terms (React.js ↔ React, PostgreSQL ↔ SQL database, FastAPI ↔ Python backend)
- Project relevance analysis against the JD
- Achievement/impact extraction (e.g., "improved performance by X%")
- Explainable AI output — not just a score, but *why* it matched, what's missing, and supporting evidence

### Dashboard
- Candidate comparison table (Match %, Skills, Experience, Missing Skills)
- Charts: skill distribution, experience spread, education breakdown, requirement coverage

### Professional / Compliance Features
- PII detection & redaction (phone, email, address, etc.)
- Bias-aware screening — protected/personal attributes excluded from ranking; criteria kept transparent and job-related
- Human-in-the-loop review — recruiter can accept/reject/override AI output; AI score and recruiter decision stored separately
- Configurable scoring weights (e.g., Skills 40%, Experience 25%, Projects 15%, Education 10%, Certifications 10%)
- Recruiter feedback loop (Relevant / Not relevant / Missing required skill) to improve future screening

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js |
| Backend | FastAPI |
| LLM | OpenAI API (or equivalent LLM provider) |
| Embeddings | Sentence Transformers / OpenAI Embeddings |
| Vector DB | FAISS or ChromaDB |
| Database | PostgreSQL |
| Resume Parsing | PyMuPDF, python-docx |
| Auth | JWT / OAuth |
| Deployment | Docker + AWS / Render / Railway |

---

## 4. Module Breakdown

Each module below is scoped to be assignable to one person or a small sub-team. Modules list their own tasks, tech, inputs/outputs, and dependencies so work can run in parallel where possible.

### Module 1 — Resume & JD Ingestion
- **Tasks:** File upload API, PDF/DOCX text extraction, JD paste/upload handling, raw-text storage
- **Tech:** FastAPI, PyMuPDF, python-docx, PostgreSQL
- **Output:** Clean extracted text for resumes + JD, stored with metadata
- **Depends on:** Nothing (foundation module — build first)

### Module 2 — Information Extraction Engine
- **Tasks:** Extract skills (technical/soft/tools/languages/certifications), experience (companies, roles, duration), education, certifications from raw text
- **Tech:** LLM API / NLP pipeline, regex + LLM hybrid parsing
- **Output:** Structured JSON profile per resume and per JD
- **Depends on:** Module 1

### Module 3 — Semantic Matching Engine
- **Tasks:** Generate embeddings for resumes and JD, semantic similarity scoring, related-term matching (e.g., React.js ↔ React), project-relevance scoring
- **Tech:** Sentence Transformers/OpenAI embeddings, FAISS/ChromaDB
- **Output:** Raw match score + matched/missing requirement lists per resume
- **Depends on:** Module 2

### Module 4 — Scoring, Ranking & Explainability
- **Tasks:** Configurable weighted scoring (skills/experience/projects/education/certs), candidate ranking logic, achievement/impact detection, "why matched / what's missing / evidence" explanation generator
- **Tech:** FastAPI service layer, LLM for explanation text
- **Output:** Final explainable score + rank per candidate
- **Depends on:** Module 3

### Module 5 — Privacy & Fairness Layer
- **Tasks:** PII detection/redaction, exclusion of protected attributes (gender, religion, caste, age, photo, etc.) from scoring logic, transparency logging of criteria used
- **Tech:** Regex/NER for PII, rule-based filters in the scoring pipeline
- **Output:** Redacted candidate view + bias-safe scoring guarantees
- **Depends on:** Module 2 (runs alongside Module 3/4)

### Module 6 — Recruiter Dashboard (Frontend)
- **Tasks:** Comparison table UI, charts (skill distribution, experience, education, requirement coverage), candidate detail view with explainability panel
- **Tech:** React/Next.js, a charting library (e.g., Recharts/Chart.js)
- **Output:** Working recruiter-facing dashboard
- **Depends on:** Module 4 (needs scored data to render)

### Module 7 — Human-in-the-Loop Review
- **Tasks:** Accept/reject/override UI and API, storing recruiter decisions separately from AI score, recruiter feedback capture (Relevant / Not relevant / Missing skill)
- **Tech:** FastAPI, PostgreSQL, React/Next.js
- **Output:** Review workflow + feedback data for future model tuning
- **Depends on:** Module 6

### Module 8 — Auth, Infra & Deployment
- **Tasks:** JWT/OAuth authentication, environment/config management, Docker containerization, CI basics, deployment to AWS/Render/Railway
- **Tech:** JWT/OAuth, Docker, chosen cloud platform
- **Output:** Deployed, authenticated, production-ready app
- **Depends on:** Runs in parallel from Phase 1 onward; finalized last

---

## 5. Development Phases

Every phase ends with a **mandatory testing & review gate** before the next phase starts — no phase begins until the previous one's bugs are triaged and closed (or explicitly deferred with sign-off).

### Phase 1 — Planning & Foundation
- Finalize database schema, API contracts, and folder structure
- Set up repo, environments, and Module 1 (ingestion)
- **Testing gate:** Validate upload works for varied resume formats (PDF/DOCX, different layouts); confirm schema supports all planned fields; peer review of API contracts

### Phase 2 — Extraction Engine
- Build Module 2 (skills/experience/education/certification extraction)
- **Testing gate:** Run extraction against a diverse sample set (10–20 real/sample resumes); manually verify extracted fields; log and fix misclassification bugs before proceeding

### Phase 3 — Semantic Matching
- Build Module 3 (embeddings, vector DB, similarity scoring, related-term matching)
- **Testing gate:** Sanity-check match scores against manually-judged resume/JD pairs; verify semantic matches (e.g., React.js ↔ React) actually resolve correctly; regression test Module 2 outputs still feed in cleanly

### Phase 4 — Scoring & Explainability
- Build Module 4 (weighted scoring, ranking, explainable output)
- **Testing gate:** Confirm explanations are consistent with the underlying evidence (no hallucinated reasoning); verify configurable weights actually change rankings as expected; edge-case test (empty resume, missing sections)

### Phase 5 — Privacy & Fairness
- Build Module 5 (PII redaction, bias-aware filtering)
- **Testing gate:** Test PII redaction against resumes containing phone/email/address in varied formats; confirm protected attributes never influence the score (audit test cases); document the transparent scoring criteria

### Phase 6 — Dashboard
- Build Module 6 (comparison table, charts, candidate detail view)
- **Testing gate:** Cross-browser/responsive UI check; verify dashboard numbers match backend output exactly; usability pass with a non-technical reviewer (simulate a recruiter's first use)

### Phase 7 — Human-in-the-Loop & Feedback
- Build Module 7 (accept/reject/override, feedback capture)
- **Testing gate:** Verify recruiter overrides persist and don't overwrite the original AI score; confirm feedback data is stored correctly for later analysis; workflow/UX test end-to-end

### Phase 8 — Auth, Deployment & Final QA
- Finalize Module 8 (auth, Docker, deployment)
- **Testing gate:** Full end-to-end run (upload → match → rank → review → export) on a staging environment; basic load test with a batch of resumes; security review (auth flows, PII handling, no secrets in code); final regression pass across all modules

---

## 6. Testing & Review Protocol (applies after every phase, not just at the end)

1. **Unit testing** — test each module's core functions in isolation
2. **Integration testing** — verify the module works correctly with the modules it depends on
3. **Peer code review** — no merge to main without at least one reviewer
4. **Bug log & triage** — every bug found gets logged, prioritized, and fixed (or explicitly deferred) before moving to the next phase
5. **Regression check** — confirm earlier phases still work after new changes
6. **Documentation update** — update this README/module docs to reflect what was actually built

---

## 7. Suggested Folder Structure

```
ai-resume-screener/
├── backend/
│   ├── app/
│   │   ├── ingestion/        # Module 1
│   │   ├── extraction/       # Module 2
│   │   ├── matching/         # Module 3
│   │   ├── scoring/          # Module 4
│   │   ├── privacy/          # Module 5
│   │   ├── review/           # Module 7
│   │   ├── auth/             # Module 8
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/            # Module 6 (dashboard)
│   │   └── ...
│   └── package.json
├── docs/
│   └── api-contracts.md
├── docker-compose.yml
└── README.md
```

---

## 8. Environment Variables (placeholder — fill in per environment)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `LLM_API_KEY` | LLM provider API key |
| `VECTOR_DB_PATH` / `VECTOR_DB_URL` | FAISS index path or ChromaDB connection |
| `JWT_SECRET` | Auth token signing secret |
| `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` | If using OAuth login |

---

## 9. Contribution Guidelines

- Pick up one module at a time from the table in Section 4; note dependencies before starting.
- Branch naming: `module-<number>-<short-name>` (e.g., `module-3-semantic-matching`)
- Open a PR at the end of each module/phase — no direct pushes to `main`.
- Every PR must pass the relevant tests in Section 6 before merge.
- Update the module's section in this README if scope or design changes during development.

---

## 10. License

Add your chosen license here (e.g., MIT) before publishing the repository publicly.
