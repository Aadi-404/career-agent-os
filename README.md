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

It returns normalized JD text, extracted skills, experience range, location, work mode, responsibilities, and warnings.

## Level 2 Scoring

The analyzer now returns:

```text
technicalMatchScore
shortlistingScore
interviewReadinessScore
overallOpportunityScore
scoreBreakdown
shortlistingFactors
recommendedAction
```

The score is calculated by the explainable scoring engine. LLM mode still generates coaching content, but the numeric score is attached by the backend scoring layer.

The request also accepts:

```text
preparationPlanDays
```

Default is `7`. Valid range is `1` to `30`.
