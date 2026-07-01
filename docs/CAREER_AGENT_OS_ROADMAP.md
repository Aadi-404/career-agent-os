# Career Agent OS Roadmap

## Goal

Career Agent OS is not only a resume analyzer. The goal is to become a career decision and interview preparation system for job switching, especially for fullstack and AI-oriented developers in the Indian market.

The app should answer practical questions:

- Should I apply to this role?
- Why is my resume a strong or weak fit?
- What topics should I prepare for this company and role?
- What shortlisting factors can reduce my chances?
- How should I rewrite my resume without inventing experience?
- What interview cross-questions should I expect?

## Core Design Principle

The scoring should not depend only on the LLM.

Use this split:

```text
Algorithm calculates.
LLM explains and coaches.
```

Why:

- LLM scores can be inconsistent.
- Algorithmic scoring is easier to debug.
- Score breakdowns are easier to explain in interviews.
- Future research and embedding layers can plug into the same contract.

## Current Level 1

Level 1 is the resume and JD technical fit analyzer.

It already supports:

- Resume text input
- Resume upload for TXT, PDF, DOCX
- Mock and live LLM modes
- Groq, OpenAI, and Gemini provider selection
- Technical match score
- Matching skills
- Weakly evidenced skills
- Missing skills
- Resume improvements
- Interview questions
- Cross-questions
- System design readiness
- 7-day preparation plan

## Level 1.5: Resume Normalization and Explainable Scoring

### Problem

Raw PDF/DOCX extraction can produce noisy text:

```text
Used
ASP.NET Core, EF, and Angular
Used
SQL Server
Implemented
CRUD operations
```

This is poor input for analysis because sections and bullet relationships are unclear.

### Flow

```text
Upload resume
-> Extract raw text
-> Normalize resume
-> User reviews/edits normalized text
-> Parse JD
-> User reviews/edits normalized JD text
-> Analyze against JD
```

### Resume Normalization Output

The backend creates:

- Profile
- Experience
- Projects
- Skills
- Education
- Achievements
- Certifications
- Warnings

Example:

```json
{
  "profile": {
    "name": "Aditya Rana",
    "location": "Navi Mumbai",
    "summary": "Full-stack .NET developer with ASP.NET Core, C#, SQL Server, Angular and production support experience."
  },
  "experience": [],
  "projects": [],
  "skills": [".NET", "ASP.NET", "C#", "SQL", "Angular"],
  "warnings": ["Projects section was not confidently detected."]
}
```

### Explainable Scoring Layers

The technical score is split into multiple scored categories.

For a 0-1 year candidate, the app gives more importance to:

- DSA and coding
- Core skills
- Projects
- Fullstack basics
- Database basics

For a 2-4 year candidate, the app gives more importance to:

- Project ownership
- Backend/frontend depth
- Database depth
- Production debugging
- Cloud/DevOps basics
- System design basics

For a 5+ year candidate, the app gives more importance to:

- Architecture
- System design
- Scalability and reliability
- Team ownership
- Cloud/DevOps
- Domain depth

### Score Breakdown Example

```json
{
  "technicalMatchScore": 64,
  "scoreBreakdown": [
    {
      "category": "experienceFit",
      "weight": 10,
      "score": 57,
      "weightedScore": 5.7,
      "reason": "JD expects at least 2 years; candidate has 1 year."
    },
    {
      "category": "coreSkills",
      "weight": 20,
      "score": 75,
      "weightedScore": 15,
      "reason": "Matched extracted JD skills: ASP.NET Core, C#, SQL."
    }
  ]
}
```

## Level 2: Shortlisting and Opportunity Scoring

Technical fit is not the same as shortlisting chance.

Level 2 adds hiring practicality signals:

- Location fit
- Preferred locations
- Notice period
- Work mode preference
- Relocation openness
- Current CTC
- Expected CTC
- Experience range fit

Protected attributes such as gender must not affect scoring.

### Level 2 Scores

The app now separates:

- `technicalMatchScore`
- `shortlistingScore`
- `interviewReadinessScore`
- `overallOpportunityScore`

Example formula:

```text
overallOpportunityScore =
technicalMatchScore * 0.45
+ shortlistingScore * 0.30
+ interviewReadinessScore * 0.25
```

### Shortlisting Factor Example

```json
{
  "factor": "Notice period",
  "impact": "neutral",
  "reason": "60-day notice is common but weaker than immediate or 30-day availability."
}
```

## Current Implementation Slice

This slice adds:

- `POST /ai/resume/normalize`
- `POST /ai/jd/parse`
- Structured resume normalization models
- Structured JD parsing models
- Experience-wise technical scoring weights
- Score breakdown response fields

## Phase 5: Extension and Production Readiness

Completed:

- Docker-ready frontend and backend setup.
- PostgreSQL-only persistence path.
- Browser extension setup and session-token flow.
- Extension diagnostics from the web app.
- Real-site extension validation records for LinkedIn, Naukri, Indeed, company pages, or manual paste fallback.

## Phase 6: Evaluation and Tuning Groundwork

Started:

- Score feedback labels are stored without making another LLM call.
- Feedback tracks expected fit, score accuracy, application outcome, algorithm score, and fit category.
- The frontend has a dedicated Score Evaluation task.
- The Score Evaluation task now shows calibration signals: accuracy rate, average score by feedback type, outcome counts, and a tuning recommendation.
- The extension popup can save parser quality feedback after real job-page testing.
- Evaluation labels can be exported/imported as JSON datasets.
- Calibration is segmented by role family so `.NET`, Java, Python, Frontend, Data/AI, and Cloud/DevOps can be tuned separately.
- Scoring calibration settings are now editable from the Admin settings UI.
- The matching engine can apply saved role-family weights while keeping score breakdowns explainable.
- Calibration recommendations can propose role-family weight changes from labelled feedback.
- Recommended weights are applied to a draft first and require explicit admin save approval.
- Scoring calibration changes are audited with before/after weights and change source.
- Previous scoring weights can be restored from the audit history.
- A system diagnostics endpoint and Settings panel show database, AI, embedding, parser, CORS, and workspace health.
- A production readiness endpoint and Settings panel flag deployment blockers before hosting the app publicly.
- User-scoped APIs can require `X-Session-Token` ownership checks by enabling `REQUIRE_USER_AUTH`.
- Settings includes a basic known-users panel for multi-user deployment checks.
- Admin-only guards now protect admin and scoring settings APIs when auth enforcement is enabled.
- `ADMIN_USER_IDS` bootstraps first admin users during session claim/update.
- Password-ready web auth now supports `/auth/register` and `/auth/login` with salted password hashes and session-token issuance.
- The Settings UI is role-aware and disables admin mutation controls for non-admin sessions.
- Backend responses now carry `X-Request-ID` and log request completion/error events for production tracing.
- CI runs backend tests, frontend build, deployment script checks, and extension packaging on push/PR.
- Web and extension session controls now support explicit reconnect/clear flows.
- Deployment tooling includes PostgreSQL JSON backup export for data safety reviews.
- Deployment tooling includes a local/dev JSON restore utility.
- The web app has an editable workspace user selector for multi-user testing.

Why this matters:

- Parser bugs can be tracked per website.
- Scoring can later be tuned from real examples instead of guesswork.
- It creates the dataset needed for calibration, regression tests, and future ML refinement.
- Dynamic requirement match matrix for JD requirement to resume evidence mapping
- JD requirement extraction from actual JD wording instead of a fixed skill whitelist
- Provider-backed embedding similarity for meaning-based JD/resume evidence matching
- Local embedding fallback for mock/offline mode and live provider failures
- Structured resume editor after normalization for correcting parsed sections before analysis
- Shortlisting score response fields
- Opportunity score response fields
- Frontend shortlisting inputs
- Frontend normalized resume review button
- Frontend parsed JD review button and extracted requirement summary
- Dynamic preparation plan length input, defaulting to 7 days
- Frontend score breakdown and shortlisting factor panels

## Future Level 2.5: Research-Grounded Company and Role Insights

This should not be mixed directly into the current analyzer yet.

Future research agent responsibilities:

- Search similar job posts
- Search company interview experiences
- Search role-specific topic patterns
- Search market demand signals
- Build company-specific topic preferences
- Cite sources used for weighting

Example:

```text
Any company or role
-> extract requirements from the JD text itself
-> match each requirement to resume evidence
-> score exact proof, weak proof, semantic proof, and missing proof
```

## Future Level 3: Market Opportunity Score

Market opportunity should use recent web/research signals:

- Similar job posting frequency
- Role demand by location
- Skill demand trend
- Experience band demand
- Company hiring activity
- Salary/CTC trend if available

This should produce:

- `marketOpportunityScore`
- `trend`
- `signals`
- `sources`

## Interview Explanation Points

### Why not use only LLM scoring?

LLM scoring is opaque and can be inconsistent. The app uses deterministic scoring categories and lets the LLM explain, coach, and generate preparation guidance.

### Why not directly feed raw PDF text?

PDF and DOCX extraction can break layout. Normalization creates structured sections and lets the user review the resume before analysis.

### Why combine lexical, semantic, and structured scoring?

Lexical matching catches hard requirements. Semantic matching catches meaning and synonyms. Structured rules handle years, location, notice period, and CTC better than free-form LLM reasoning.

### Why remove the fixed skill whitelist?

A fixed list makes the app biased toward one stack. If the code only knows `.NET`, `React`, and `Azure`, it can miss roles asking for `Kafka`, `Salesforce`, `SAP`, `LangChain`, `GraphQL`, `Rust`, or any future technology. The current scorer extracts requirements from the JD text itself and then uses embeddings to match those requirements to resume evidence.

### Why use a real embedding model?

Rules can say `AZ-900` is related to cloud, but a trained embedding model is better at comparing phrases that use different wording. For example, it can compare a JD requirement like `cloud fundamentals and deployment awareness` with resume evidence like `completed Azure Fundamentals certification and supported release validation`. This gives the scorer a semantic signal before deciding whether the evidence is strong, weak, or missing.

### Why keep a local fallback?

Embedding APIs can fail because of missing keys, network issues, limits, or provider outages. The app should still produce an explainable result in mock/offline mode. The local fallback is weaker than a trained model, but it keeps the workflow usable and makes provider failures visible in the match reason.

### Why exclude gender from scoring?

Gender is a protected attribute. It should not influence technical fit, shortlisting score, or opportunity score.
