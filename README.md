# Career Agent OS

Level 1 is a resume and job-description technical fit analyzer.

## Current Scope

- FastAPI AI service with a strict Pydantic request/response contract.
- Mock analyzer response and live LLM mode for Groq, OpenAI, and Gemini.
- React + Vite frontend for fixed input fields and structured result rendering.
- Resume input can be pasted as text or extracted from `.txt`, `.pdf`, or `.docx`.
- Level 1.5 explainable scoring with experience-wise score breakdowns.
- Level 2 shortlisting and opportunity scoring using location, notice period, work mode, and CTC context.

## Product Roadmap

GitHub-facing project status summary:

```text
PROJECT_STATUS.md
```

The step-by-step product direction is documented in:

```text
docs/CAREER_AGENT_OS_ROADMAP.md
```

Phase 5 deployment and extension validation details are documented in:

```text
docs/PHASE_5_PRODUCTION_READINESS.md
```

MVP launch status and remaining deploy blockers are documented in:

```text
docs/MVP_LAUNCH_STATUS.md
```

Project demo and interview explanation guide:

```text
docs/PROJECT_DEMO_GUIDE.md
```

Staging deployment steps are documented in:

```text
docs/STAGING_DEPLOYMENT_RUNBOOK.md
```

Deployment environment templates are available in:

```text
deployment/env
```

Current Phase 6 groundwork:

- Extension validation records: `POST /extension/validation-results`.
- Score feedback labels: `POST /evaluation/match-feedback`.
- Tuning summary: `GET /evaluation/users/{user_id}/summary`.
- Frontend task: `Score Evaluation`.
- Calibration dashboard signals: accuracy rate, bias direction, outcome counts, and average score buckets.
- Extension popup parser feedback: save page parsing quality directly from the browser extension.
- Dataset export/import: move labelled match feedback as JSON for tuning review.
- Role-family calibration: segment labels by `.NET`, Java, Python, Frontend, Data/AI, Cloud/DevOps, or General Software.
- Scoring calibration settings: edit role-family category weights from the Admin settings UI.
- Calibrated scoring: match requests can use saved user calibration without extra LLM calls.
- Calibration recommendations: propose weight changes from labelled feedback.
- Approval flow: suggestions apply to a draft first; admins must explicitly save before scoring changes.
- Scoring audit history: every saved calibration change stores before/after weights.
- Rollback: admins can restore previous scoring weights from the audit trail.
- System diagnostics: `/diagnostics/system` reports database, AI config, embedding config, parser mode, CORS, and workspace counts.
- Production readiness: `/diagnostics/production-readiness` checks deployment blockers such as database, environment mode, auth, admin bootstrap, CORS, LLM, embeddings, and JD parser setup.
- Admin runtime panel: Settings page shows operational diagnostics without making AI calls.
- Optional user auth enforcement: set `REQUIRE_USER_AUTH=true` to require `X-Session-Token` on user-scoped history, evaluation, settings, diagnostics, and extension validation APIs.
- Web session claim: frontend uses `/auth/session/claim` and stores a session token for guarded requests.
- Password-ready web auth: `/auth/register` and `/auth/login` issue the same session token shape for deployable multi-user login flows.
- Profile workspace panel: the web app shows active user, role, session state, and saved workspace counts beside login/register/logout controls.
- Admin user visibility: `/admin/users` and the Settings page show known users for deployment checks.
- Role-based admin guard: when auth is enforced, `/admin/*` and scoring settings require an admin session.
- First admin bootstrap: configure `ADMIN_USER_IDS` so listed users are promoted to `admin` on session claim/update.
- Request tracing: every backend response includes `X-Request-ID`, and unhandled errors return a safe request id instead of raw internals.
- CI workflow: GitHub Actions runs backend tests, frontend build, deployment script compile checks, and extension packaging dry run.
- Session controls: web and extension UIs can refresh or clear saved session tokens when auth state is stale.
- Workspace user selector: the web app can switch the active user id instead of being locked to `local-aditya`.
- Role-aware Settings UI: scoring recommendations, saves, restores, and known-user refresh controls are disabled unless the active session is admin.
- Extension auth alignment: the extension can login/register with password auth, load saved resumes through the session, parse/paste a JD, and match a saved resume.
- Resume library reuse: the matching flow can load saved PostgreSQL resume snapshots back into the parser/review/scoring steps.
- Free/premium visual gating: score output is presented as the free module, while preparation, interview, cross-question, and rewrite artifacts are presented as premium modules.
- Entitlement state: the workspace now tracks Free, Premium, and Admin access so premium actions can be locked or unlocked consistently.
- JD library reuse: saved PostgreSQL job descriptions can be loaded back into the matching flow for repeat comparisons.
- Persistent subscription tier: user records store the Free/Premium tier and expose a guarded tier update API for deployed sessions.
- Billing-ready metadata: user records can store subscription status, plan id, provider customer id, provider subscription id, and billing period end.
- Saved comparison workflow: the web app can compare saved resumes against saved JDs with score-only runs capped to avoid accidental spend.
- Research notes workspace: the web app can save manual or generated company, role, market, and interview research notes with key signals, preparation topics, and source references for the future research-agent phase.
- Research-aware preparation: saved research notes can be passed into preparation intelligence so company/role signals influence the study plan without rerunning matching.
- Citation quality checks: research sources are labelled as verified URL, manual note, weak, or uncited, with validation issues shown in the UI.
- Research enrichment adapter: `RESEARCH_PROVIDER=local` creates citation-ready query plans, while `RESEARCH_PROVIDER=google` can fetch cited Google Custom Search results when `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID` are configured.
- Typed research enrichment: generated research drafts now separate company, interview, and market signals before they are saved or cited.
- Research snippet extraction: cited search result titles/snippets can add preparation topics and live-source signals without another LLM call.
- Research page extraction: cited pages are fetched with safe timeouts and reduced to readable text when available, enriching draft evidence without another LLM call.
- Research synthesis: cited source patterns produce first-pass market opportunity and role/company preparation signals without another LLM call.
- Research provider visibility: generated drafts show whether local planning or live Google search was used, including provider warnings.
- Extension research handoff: parsed or manually pasted job pages can open the web Research Notes task with role, company, JD text, and source URL prefilled.
- Apply decisioning: the web app can combine score, opportunity signals, and saved research notes into apply / prepare first / selective apply / skip guidance.
- Evidence-constrained resume rewrite: the web app can generate safer rewrite suggestions labelled as existing evidence, needs verification, or gap-only.
- Rewrite approval workflow: safe or user-verified suggestions can be applied into the structured resume draft, while gap-only suggestions stay blocked from becoming resume claims.
- Accepted rewrite audit: applied bullets are saved in PostgreSQL with proof-safety, target section, and linked analysis/resume/JD context when available.
- Resume version snapshots: accepted rewrites can preserve the full structured resume draft for future compare and rollback controls.
- Resume version controls: saved versions can be compared against the current draft and restored into the review editor.
- Restore audit history: each resume version restore is persisted so rollback decisions remain traceable.

## Run AI Service

```powershell
cd C:\Code\AI\career-agent-os\ai-service
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Swagger:

```text
http://localhost:8000/docs
```

Readiness:

```text
http://localhost:8000/ready
```

## Run Frontend

```powershell
cd C:\Code\AI\career-agent-os\frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## Docker Compose

```powershell
cd C:\Code\AI\career-agent-os
docker compose up --build
```

Services:

```text
Frontend: http://localhost:8080
AI service: http://localhost:8001
PostgreSQL: localhost:5432
```

## Deployment Env Profiles

Use the templates in `deployment/env` when configuring hosting environments:

```text
backend.local.env.example
backend.staging.env.example
backend.production.env.example
frontend.local.env.example
frontend.staging.env.example
frontend.production.env.example
```

Production should use `ENVIRONMENT=production`, `REQUIRE_USER_AUTH=true`, a managed PostgreSQL `DATABASE_URL`, deployed CORS origins, `BILLING_WEBHOOK_SECRET`, and backend-only provider keys.
Set `LOG_LEVEL=INFO` for normal deployment logs or `LOG_LEVEL=DEBUG` only during short debugging sessions.

Use [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md) before staging or production deploys.

Run deployment smoke checks with:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api http://localhost:8000 --frontend http://localhost:5173
```

Run the full local release verification bundle with:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\verify_release.py
```

For production-style smoke checks, include auth, quota, checkout, billing webhook, and extension packaging:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api https://api.your-domain.com --frontend https://app.your-domain.com --user-id your-user-id --session-token your-session-token --billing-webhook-secret your-webhook-secret --check-extension-package --strict-production
```

Export a PostgreSQL JSON backup with:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\backup_database.py --pretty
```

Seed a demo workspace for project reviews with:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\seed_demo_data.py --reset --premium --print-token
```

Admins can also seed the demo workspace from:

```text
Task: Scoring Settings -> Demo -> Seed Demo Data
```

Restore a local/dev database from a JSON backup with:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\restore_database.py deployment\backups\career-agent-os-backup.json --yes
```

For a single-host Docker deployment, copy and edit `deployment/env/compose.production.env.example`, then run:

```powershell
docker compose --env-file deployment/env/compose.production.env -f docker-compose.production.example.yml up --build -d
```

Before running the production compose stack, rehearse the deployment assets locally:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\production_rehearsal.py --api https://api.your-domain.com --web https://app.your-domain.com
```

If Docker is installed and running, include compose validation:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\production_rehearsal.py --api https://api.your-domain.com --web https://app.your-domain.com --compose-config
```

## Browser Extension

Load the unpacked extension from:

```text
C:\Code\AI\career-agent-os\extension
```

Then open the web app and use:

```text
Task 5 -> Extension Setup -> Check Extension Readiness
```

Package a release build with the deployed backend URL:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\package_extension.py --api https://api.your-domain.com --web https://app.your-domain.com --version 0.1.0
```

## Level 1 Request Shape

```json
{
  "resumeText": "string",
  "jobDescriptionText": "string",
  "candidateContext": {
    "targetRole": "string",
    "experienceYears": 3,
    "currentStack": ["string"],
    "targetMarket": "string"
  }
}
```

## Next Implementation Step

The analyzer supports two modes:

```text
LLM_MODE=mock
```

Use this for frontend and contract testing without API cost.

```text
LLM_MODE=live
```

Use this to call a real provider.

## LLM Providers

Set these in `ai-service/.env`.

Groq:

```text
LLM_MODE=live
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
LLM_API_KEY=your_groq_key
GROQ_API_KEY=your_groq_key
```

OpenAI:

```text
LLM_MODE=live
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
LLM_API_KEY=your_openai_key
OPENAI_API_KEY=your_openai_key
```

Gemini:

```text
LLM_MODE=live
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=your_gemini_key
GEMINI_API_KEY=your_gemini_key
GOOGLE_API_KEY=your_google_ai_studio_key
```

For Gemini, the backend accepts `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or the generic `LLM_API_KEY`.

The service still returns the same Pydantic response contract in both `mock` and `live` mode.

The frontend can override mode, provider, and model per request. API keys stay in the backend `.env`.

Research enrichment:

```text
RESEARCH_PROVIDER=google
GOOGLE_API_KEY=your_google_custom_search_key
GOOGLE_SEARCH_ENGINE_ID=your_google_programmable_search_engine_id
```

When these are not set, research notes still use the local citation-ready query plan.

The frontend API base URL defaults to `http://localhost:8000`. Override it when needed:

```text
VITE_API_BASE_URL=http://localhost:8001
```

## Embedding Providers

Embeddings are used by the requirement matcher when exact aliases and category rules are not enough. This is what lets the app connect meaning, for example `cloud basics` in a JD with `AZ-900`, `AWS Cloud Practitioner`, or `Google Cloud Digital Leader` in a resume.

Set these in `ai-service/.env`:

```text
EMBEDDING_PROVIDER=auto
EMBEDDING_MODEL=
EMBEDDING_TIMEOUT_SECONDS=20
EMBEDDING_FALLBACK_LOCAL=true
```

Provider options:

```text
auto
gemini
openai
local
```

`auto` prefers the configured live provider when a key is available:

- Gemini default embedding model: `gemini-embedding-2`
- OpenAI default embedding model: `text-embedding-3-small`
- Local fallback model: `hashing-256`

The local fallback is intentionally kept so mock/offline analysis still works. If the live embedding API fails once during a run, the scorer falls back to the local vectorizer for the rest of that run instead of retrying every requirement.

## Resume Upload

The upload endpoint is:

```text
POST /ai/resume/extract
```

Supported files:

```text
.txt
.pdf
.docx
```

The endpoint extracts resume text and detects simple signals like emails, phone numbers, and section names. The extracted text is then used by the analyzer.

## Resume Normalization

The normalization endpoint is:

```text
POST /ai/resume/normalize
```

Input:

```json
{
  "rawResumeText": "string"
}
```

It returns normalized resume text, a structured resume draft, and warnings for sections that need manual review.

Recommended flow:

```text
Upload resume -> extract text -> normalize resume -> review/edit resume -> parse JD -> review/edit JD -> analyze
```

## JD Parsing

The JD parsing endpoint is:

```text
POST /ai/jd/parse
```

Input:

```json
{
  "rawJobDescriptionText": "string"
}
```

It returns normalized JD text, dynamically extracted skill/requirement phrases, experience range, location, work mode, responsibilities, and warnings.

## Level 2 Scoring

The analyzer now returns:

```text
technicalMatchScore
shortlistingScore
interviewReadinessScore
overallOpportunityScore
scoreBreakdown
requirementMatches
shortlistingFactors
recommendedAction
```

The score is calculated by the explainable scoring engine. LLM mode still generates coaching content, but the numeric score is attached by the backend scoring layer.

`requirementMatches` is the requirement-level evidence matrix. It maps extracted JD requirements to the strongest resume evidence, evidence source, match type, and score.

Requirement matching no longer depends on a fixed skill whitelist. The scorer first extracts requirement phrases from the actual JD, including comma-separated skills and responsibility statements, then matches those dynamic requirements against resume evidence. It uses phrase overlap, evidence-source strength, and provider-backed embedding similarity for meaning-based matches. If no embedding provider is configured, it falls back to the local deterministic vectorizer.

Example:

```text
JD: Required Skills: Kafka, Redis, GraphQL, LangChain, vector databases.
Resume: Built event streaming workers with Kafka and improved Redis cache latency.
Result: Kafka and Redis become dynamic requirements and are matched without being prelisted in code.
```

After resume normalization, the frontend also exposes a structured resume editor for profile, experience, projects, skills, education, achievements, and certifications. Edits regenerate the resume text used for analysis.

The request also accepts:

```text
preparationPlanDays
```

Default is `7`. Valid range is `1` to `30`.
