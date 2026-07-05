# Career Agent OS Project Status

## What This Project Is

Career Agent OS is a full-stack AI career workspace for resume-to-job-description matching, interview preparation, saved job-search history, and browser-extension assisted job analysis.

The product direction is:

```text
Resume scorer -> career workspace -> browser job companion -> agentic career OS
```

## Current Build Status

Status: MVP is locally functional and close to staging-ready.

Core app is implemented. Remaining public-launch work is deployment-specific: staging deploy, real job-site extension validation, production secrets, billing setup, and real labelled tuning data.

## Completed Product Capabilities

| Area | Status | Highlights |
| --- | --- | --- |
| Resume/JD scoring | Complete | Resume/JD parsing, review/edit step, score-only flow. |
| Explainable matching | Complete | Score breakdown, requirement match matrix, semantic evidence matching. |
| Shortlisting signals | Complete | Location, work mode, notice period, experience band, opportunity score. |
| Optional AI modules | Complete | Preparation plan, gap report, interview questions, cross-questions, resume improvements. |
| Cost control | Complete | Mandatory score call separated from optional premium-style AI calls. |
| Persistence | Complete | PostgreSQL users, resumes, JDs, analyses, comparisons, prep sessions, opportunities. |
| Auth | Complete | Password auth, session tokens, guarded user APIs, admin guard. |
| Browser extension | Mostly complete | Saved resume matching, page parsing, manual JD fallback, parser feedback, research handoff. |
| Evaluation/tuning | Complete groundwork | Feedback labels, role-family calibration, audit history, rollback. |
| Admin readiness | Complete groundwork | Diagnostics, production readiness, usage dashboard, billing handoff, launch tracker. |
| Deployment tooling | Complete groundwork | Dockerfiles, compose examples, smoke check, production rehearsal, backup/restore. |
| Research memory | Started | Manual and generated company/role/interview research notes saved in PostgreSQL for future cited research agents. |
| Apply decisioning | Started | Score + research based apply / prepare / skip decision module. |
| Resume rewrite | Started | Evidence-constrained rewrite suggestions with proof-safety labels. |

## AI Design

The app follows this rule:

```text
Algorithm calculates. LLM explains and coaches.
```

Why:

- Numeric scores must be repeatable and explainable.
- LLM output is better for coaching content than deterministic scoring.
- Optional modules can be called one at a time to reduce cost.
- Saved results can be reused from PostgreSQL.

## AI Concepts Used

| Concept | Implementation |
| --- | --- |
| Semantic embeddings | Requirement-to-resume evidence matching beyond exact keywords. |
| Deterministic scoring | Stable score breakdowns and opportunity scoring. |
| Structured extraction | Resume and JD normalization into editable sections. |
| LLM generation | Optional prep plans, questions, cross-questions, improvements. |
| Calibration loop | Feedback labels and role-family weight tuning. |
| Future RAG | Saved resumes, JDs, analyses, feedback, and prep progress can become memory. |
| Future agents | Research, rewrite, apply-decision, and prep-tracker agents are planned. |

## Tech Stack

- Frontend: React, TypeScript, Vite, CSS.
- Backend: Python, FastAPI, Pydantic.
- Database: PostgreSQL.
- Extension: Manifest V3 JavaScript browser extension.
- AI providers: Groq, OpenAI, Gemini.
- Embeddings: provider-backed with local fallback.
- Deployment: Docker, Docker Compose examples, GitHub Actions CI.

## Demo Path

Best demo path:

1. Open the web app.
2. Login as an admin or local workspace user.
3. Go to `Scoring Settings -> Demo -> Seed Demo Data`.
4. Open History and show saved resumes/JDs/analysis/opportunities.
5. Open the saved score and show requirement match matrix.
6. Show Preparation Progress.
7. Show Score Evaluation.
8. Show Extension Setup.
9. Show Settings diagnostics and Manual Launch Tracker.

Default seeded demo login:

```text
User ID: demo-aditya
Password: DemoPass123!
```

## Verification Commands

Backend:

```powershell
cd ai-service
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall app
```

Frontend:

```powershell
cd frontend
npm run build
npm run smoke
```

Deployment tooling:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\verify_release.py
.\ai-service\.venv\Scripts\python.exe deployment\production_rehearsal.py --api http://127.0.0.1:8001 --web http://127.0.0.1:8080
.\ai-service\.venv\Scripts\python.exe -m py_compile deployment\smoke_check.py deployment\package_extension.py deployment\backup_database.py deployment\restore_database.py deployment\production_rehearsal.py deployment\seed_demo_data.py deployment\verify_release.py
node extension\test-content-script.mjs
```

## Remaining Before Public Launch

- Deploy staging backend/frontend with real staging domains.
- Configure production/staging secrets outside git.
- Run smoke checks against staging.
- Validate browser extension on LinkedIn, Naukri, Indeed, and one company career page.
- Configure real billing checkout or keep manual premium unlock for MVP demo.
- Collect labelled resumes/JDs for scoring calibration.
- Decide hosting provider and production backup policy.

## Future Phases

### Phase 7: Research-Grounded Intelligence

Status: Started.

Built:

- Manual research-note workspace memory.
- Score-based research note draft generation.
- Browser extension handoff can prefill research notes from parsed job pages.
- PostgreSQL storage for company, role, market, interview, and manual notes.
- Saved key signals, preparation topics, and source references.
- Preparation intelligence can use saved research notes as context.
- Demo seed includes a research note.
- Citation quality checks for research sources, including verified URL, manual note, weak, and uncited states.
- Research enrichment provider interface with a local query-plan provider and Google provider configuration hooks.
- Research enrichment now separates company, interview, and market signals before they are saved into draft notes.
- Google research provider can execute Custom Search, convert results into verified URL citations, and fall back to local query plans when keys or HTTP calls fail.
- Cited result snippets can add deterministic preparation topics and live-source key signals without an extra LLM call.
- Cited pages can be fetched with safe timeouts, reduced to readable text, and used for additional preparation topics and evidence signals.
- Research Notes UI shows draft provider status, verified citation counts, and provider warnings.

Remaining:

- Deepen role/company topic synthesis from extracted pages.
- Produce scored market opportunity signals from cited source patterns.

### Phase 8: Agentic Career OS

Status: Started.

Built:

- Apply-decision module using score, shortlisting, readiness, opportunity, and saved research signals.
- Evidence-constrained resume rewrite suggestions.
- Rewrite approval workflow that applies safe or user-verified suggestions into the structured resume draft while blocking gap-only claims.
- Accepted rewrite audit history in PostgreSQL with linked analysis/resume/JD context when available.
- Resume version snapshots after accepted rewrites, preserving the full structured resume draft.
- Resume version compare and restore controls in the rewrite workspace.
- Persisted restore audit history for resume version rollback decisions.

Remaining:

- Apply-decision agent with tool orchestration.
- Company research agent.
- Interview-prep tracker agent.
- RAG memory over saved workspace history.

## Important Docs

- `docs/CAREER_AGENT_OS_ROADMAP.md`
- `docs/MVP_LAUNCH_STATUS.md`
- `docs/PROJECT_DEMO_GUIDE.md`
- `docs/STAGING_DEPLOYMENT_RUNBOOK.md`
- `docs/PHASE_5_PRODUCTION_READINESS.md`
- `docs/DEPLOYMENT_CHECKLIST.md`
