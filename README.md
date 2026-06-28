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

The step-by-step product direction is documented in:

```text
docs/CAREER_AGENT_OS_ROADMAP.md
```

Phase 5 deployment and extension validation details are documented in:

```text
docs/PHASE_5_PRODUCTION_READINESS.md
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

## Browser Extension

Load the unpacked extension from:

```text
C:\Code\AI\career-agent-os\extension
```

Then open the web app and use:

```text
Task 5 -> Extension Setup -> Check Extension Readiness
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
