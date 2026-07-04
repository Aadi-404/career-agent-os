# Career Agent OS Project Demo Guide

Use this guide when presenting Career Agent OS in a portfolio review, interview, or freelance/gig conversation.

## One-Line Pitch

Career Agent OS is a full-stack AI career workspace that matches resumes against job descriptions, explains the score, tracks history, prepares interview plans, and extends into job websites through a browser extension.

## Problem Statement

Most resume matchers are either keyword filters or opaque LLM prompts.

This app solves three practical problems:

- Candidates do not know whether a job is worth applying to.
- Generic ATS scores do not explain which JD requirements are actually covered.
- LLM-heavy flows can become expensive if every action generates the full report at once.

## Product Demo Flow

### 1. Login And Workspace

Show:

- User login/session.
- Workspace summary.
- Saved resume/JD/history counts.
- Free, Premium, and Admin access state.

Explain:

- Multi-user support is backed by PostgreSQL.
- Session tokens protect user-scoped APIs when `REQUIRE_USER_AUTH=true`.

### 2. Resume And JD Parsing

Show:

- Upload or paste resume.
- Parse and normalize resume.
- Review/edit structured resume sections.
- Parse JD and review extracted requirements.

Explain:

- PDF/DOCX extraction can be noisy, so the user gets an edit step before scoring.
- Resume and JD are converted into structured data first.

Expected cross-question:

```text
Why not directly send raw resume text to the LLM?
```

Answer:

```text
Raw extraction can break sections and mix bullets. Normalization plus user review reduces wrong scoring caused by parser errors.
```

### 3. Free Score Step

Show:

- Technical match score.
- Shortlisting score.
- Interview readiness score.
- Overall opportunity score.
- Score breakdown.
- Requirement match matrix.

Explain:

- The score is algorithmic and explainable.
- The LLM is used for optional coaching, not as the source of truth for numeric scoring.

Expected cross-question:

```text
Why not use only LLM scoring?
```

Answer:

```text
LLM scoring can be inconsistent and hard to debug. The app uses deterministic scoring categories and semantic requirement matching, then uses the LLM for explanations and coaching.
```

### 4. Premium Optional Modules

Show optional calls one by one:

- Preparation plan.
- Gap report.
- Interview questions.
- Cross-questions.
- Resume improvements.

Explain:

- The mandatory score call is separate from optional premium modules.
- This reduces AI cost because users only generate what they need.

Expected cross-question:

```text
How did you reduce LLM cost?
```

Answer:

```text
The app splits score, prep plan, gap report, interview questions, cross-questions, and resume improvements into separate endpoints. Saved results are reused from PostgreSQL when inputs repeat.
```

### 5. History And Progress

Show:

- Saved analyses.
- Saved resumes.
- Saved JDs.
- Saved comparisons.
- Application pipeline.
- Preparation progress tracking.

Explain:

- This turns the product into a career workspace, not just a one-time analyzer.
- Preparation memory can later become RAG context.

### 6. Browser Extension

Show:

- Extension login.
- Saved resume loading.
- Job page parsing.
- Manual JD fallback.
- Match against saved resume.
- Opportunity saved back into web history.

Explain:

- The extension is designed for LinkedIn, Naukri, Indeed, and company career pages.
- Manual paste fallback is required because job websites often change DOM structures.

Expected cross-question:

```text
How do you handle job sites where auto parsing fails?
```

Answer:

```text
The extension extracts title, company, location, and JD when possible, but always provides manual role/company/JD inputs. The important fields are JD, role, and company.
```

### 7. Admin And Launch Readiness

Show:

- Production readiness diagnostics.
- System diagnostics.
- Usage quota dashboard.
- Billing handoff.
- Demo seed button.
- Manual launch checklist.

Explain:

- Admin tools make the app deployable and reviewable.
- The launch tracker separates automated readiness checks from manual checks such as extension real-site validation.

## Architecture Summary

```text
React + Vite frontend
-> FastAPI backend
-> PostgreSQL persistence
-> Deterministic scoring engine
-> Embedding similarity layer
-> Optional LLM modules
-> Browser extension
```

## AI Concepts Used

| Concept | Usage |
| --- | --- |
| Semantic embeddings | Match JD requirements to resume evidence beyond exact keyword matching. |
| Deterministic scoring | Produce stable, explainable numeric scores. |
| LLM optional artifacts | Generate preparation plans, questions, and improvements only when requested. |
| Calibration dataset | Store feedback labels to tune scoring later. |
| Future RAG memory | Use saved resumes, JDs, analyses, prep progress, and feedback as personal context. |
| Future agents | Coordinate research, rewrite, prep, and apply-decision workflows. |

## Tech Stack

- Frontend: React, TypeScript, Vite, CSS.
- Backend: Python, FastAPI, Pydantic.
- Database: PostgreSQL.
- Extension: Chrome/Edge Manifest V3, JavaScript.
- AI providers: Groq, OpenAI, Gemini.
- Embeddings: provider-backed with local fallback.
- Deployment: Docker, Docker Compose examples, GitHub Actions CI.

## Strong Talking Points

- Score is explainable, not a black-box LLM answer.
- Resume/JD parsing has a human review step.
- AI calls are modular to control cost.
- PostgreSQL history enables multi-user deployment.
- Browser extension makes the product usable during real job search.
- Evaluation labels create a path toward data-driven tuning.
- Admin diagnostics and smoke checks show production thinking.

## Current Limitations To Mention Honestly

- Real-world extension selectors still need manual validation on job sites.
- Scoring calibration needs more labelled resumes/JDs.
- Company-specific interview research is planned for a later research-agent phase.
- Public deployment still requires real staging/production domains, secrets, and billing setup.

## Best Demo Dataset

Use:

```text
Scoring Settings -> Demo -> Seed Demo Data
```

Default demo login:

```text
User ID: demo-aditya
Password: DemoPass123!
```

Then show:

1. History dashboard.
2. Saved analysis.
3. Requirement match matrix.
4. Preparation progress.
5. Score Evaluation.
6. Extension setup.
7. Settings launch tracker.

## Interview Cross-Questions To Prepare

```text
How do embeddings improve over keyword matching?
```

Embeddings compare meaning, so phrases like `cloud fundamentals` can match Azure fundamentals certifications even if the exact wording differs.

```text
How do you prevent hallucinated resume improvements?
```

The app should generate improvements based on existing evidence. Future rewrite agents should cite the resume evidence used for each suggested bullet.

```text
How would you scale this?
```

Separate background workers for document parsing and optional AI generation, cache embeddings, rate-limit user actions, move files to object storage, and keep PostgreSQL for transactional history.

```text
How would you tune the scoring model?
```

Collect labelled outcomes, segment by role family and experience level, compare expected fit against algorithm scores, then adjust category weights through audited calibration settings.

```text
What is agentic AI in this project?
```

Current app is tool-based and modular. The future agent layer would decide which tools to call: score, research company, rewrite resume, plan prep, and track progress using workspace memory.
