# Career Agent OS MVP Launch Status

## Current Product Position

Career Agent OS is now a deployable MVP for resume-to-JD scoring, preparation planning, saved career workspace history, and browser-extension assisted job matching.

The core product rule is:

```text
Algorithm calculates. LLM explains and coaches.
```

This keeps the score explainable and repeatable while still using AI for coaching artifacts such as preparation plans, interview questions, cross-questions, and resume improvement suggestions.

## Completed Phases

### Phase 1: Resume and JD Analyzer

Status: Complete.

Built:

- Resume paste/upload support for TXT, PDF, and DOCX.
- JD input and parsing.
- Mock and live LLM modes.
- Groq, OpenAI, and Gemini provider configuration.
- Structured analyzer response contract.

Why it matters:

- This is the core user workflow: upload resume, add JD, get a technical fit score.

### Phase 1.5: Resume Normalization and Explainable Scoring

Status: Complete.

Built:

- Resume normalization endpoint.
- Structured resume editor for profile, experience, projects, skills, education, achievements, and certifications.
- JD parser with requirement extraction.
- Requirement match matrix.
- Score breakdown by explainable categories.
- Provider-backed semantic embeddings with local fallback.

Why it matters:

- Raw PDF/DOCX text is noisy. The review/edit step prevents bad parsing from silently corrupting the score.
- Requirement-level evidence makes the score defendable in an interview or product demo.

### Phase 2: Shortlisting and Opportunity Score

Status: Complete.

Built:

- Technical match score.
- Shortlisting score.
- Interview readiness score.
- Overall opportunity score.
- Location, work mode, notice period, experience, and CTC context.

Why it matters:

- A candidate can be technically good but still less likely to be shortlisted because of location, notice period, or experience-band mismatch.

### Phase 2.5: Evaluation and Calibration Groundwork

Status: Mostly complete.

Built:

- Score feedback labels.
- Score evaluation task.
- Feedback export/import dataset path.
- Role-family calibration.
- Admin calibration settings.
- Calibration recommendation draft flow.
- Scoring audit history and rollback.

Still needs:

- Real labelled resume/JD examples from your testing.
- Manual tuning review after enough examples are collected.

Why it matters:

- This creates the dataset needed to tune scoring from evidence instead of guessing weights.

### Phase 3: Preparation Intelligence

Status: Complete.

Built:

- Preparation plan generation.
- Dynamic preparation-plan days input, defaulting to 7 days.
- Resume improvements.
- Gap report.
- Interview questions.
- Cross-questions.
- Optional artifact endpoints split from the mandatory score step.

Why it matters:

- Score is the free mandatory step. Deeper guidance is optional and can be premium-positioned to control AI usage.

### Phase 4: Multi-User Workspace and History

Status: Complete.

Built:

- PostgreSQL persistence.
- User records and session tokens.
- Saved resumes.
- Saved JDs.
- Saved analyses.
- Saved comparison runs.
- Workspace analytics.
- Application pipeline status tracking.
- Preparation progress memory.

Why it matters:

- The product can support multiple users and preserve history across sessions instead of behaving like a one-time local tool.

### Phase 5: Browser Extension and Production Readiness

Status: Almost complete.

Built:

- Browser extension popup.
- Password login/register from extension.
- Extension session bootstrap.
- Saved resume matching from extension.
- Auto JD parsing from job pages with manual JD fallback.
- Role/company/JD manual input fallback.
- Parser quality feedback.
- Extension validation records.
- Extension packaging script.
- Production env templates.
- Dockerfiles and Docker Compose examples.
- Production readiness diagnostics.
- Smoke-check script.
- CI pipeline.
- Quota enforcement.
- Billing checkout handoff.

Still needs:

- Manual validation on LinkedIn, Naukri, Indeed, and at least one company career page.
- Real deployed domain values for API, web, CORS, auth, billing, and provider keys.

Why it matters:

- This is what turns the app from a local analyzer into a job-search companion that can run where the user sees job listings.

### Phase 6: Launch Hardening

Status: Started.

Built:

- Request IDs and safer error responses.
- Admin/user guard paths.
- Production diagnostics.
- Backup and restore utilities.
- Production deployment checklist.
- Production rehearsal script.
- Staging deployment runbook.
- Demo workspace seed script.
- Admin-only demo seed endpoint and Settings button.
- In-app launch checklist tracker.
- Project demo guide for portfolio and interview walkthroughs.
- CI checks for backend, frontend, deployment scripts, extension packaging, and production rehearsal.

Still needs:

- Hosted staging deployment.
- End-to-end smoke run against staging.
- First real user account and admin bootstrap check.
- Backup/restore rehearsal with non-sensitive test data.

Why it matters:

- These checks reduce deployment risk before public or portfolio usage.

## Remaining Phases

### Phase 7: Research-Grounded Market and Company Intelligence

Status: Not started.

Planned:

- Search similar job postings.
- Search recent company interview experiences.
- Extract role-specific preparation topics.
- Cite sources.
- Produce market opportunity signals.

Why it is later:

- It needs web search, citation handling, and likely more AI cost. The scoring engine should remain stable before adding research agents.

### Phase 8: Agentic Career OS

Status: Not started.

Planned:

- Apply-decision agent.
- Resume rewrite agent with evidence constraints.
- Interview-prep tracker agent.
- Company research agent.
- RAG memory over saved resumes, JDs, analyses, feedback, and preparation progress.

Why it is later:

- Agents need reliable tools, memory, guardrails, and cost control. The current modular backend creates that foundation.

## AI and System Concepts Used

| Concept | Where Used | Why Used |
| --- | --- | --- |
| Deterministic scoring | Match score, shortlisting score, opportunity score | Keeps numeric scoring explainable and testable. |
| LLM generation | Optional plans, questions, improvements, gap reports | Produces coaching content after the score step. |
| Semantic embeddings | Requirement match matrix | Matches meaning beyond exact words, such as cloud fundamentals with AZ-900. |
| Local fallback embeddings | Offline/mock/provider failure path | Keeps scoring usable without live embedding calls. |
| Structured extraction | Resume/JD normalization | Converts messy text into editable sections. |
| Calibration | Score Evaluation and Admin settings | Allows future tuning from labelled examples. |
| Usage quotas | Free/premium/admin limits | Controls AI cost and supports commercial packaging. |
| Session auth | Web and extension login | Enables multi-user history and protected APIs. |
| Future RAG memory | Planned phase | Will use saved history as context for personal career guidance. |
| Future agents | Planned phase | Will coordinate research, scoring, prep, and rewrite workflows. |

## Launch Blockers

These must be handled before a public deployment:

- Configure production `DATABASE_URL`.
- Configure `CORS_ALLOW_ORIGINS` to the deployed frontend only.
- Set `REQUIRE_USER_AUTH=true`.
- Set `ADMIN_USER_IDS` for the first admin.
- Set billing checkout and webhook values.
- Set provider API keys in backend secrets only.
- Run `/diagnostics/production-readiness` with no failed checks.
- Run `deployment/smoke_check.py` against the deployed API and frontend.
- Validate extension parsing on real job pages.

## Can Wait

These are important but not launch blockers for an MVP demo:

- Real score tuning from a large dataset.
- Company-specific interview research.
- Market demand scoring.
- Automated apply-decision agent.
- Full RAG memory.
- Extension store publishing.

## Demo Flow

Use this for project explanation:

1. Register or login.
2. Upload a resume.
3. Normalize and review/edit parsed resume sections.
4. Paste or upload a JD.
5. Review parsed JD requirements.
6. Run the free score.
7. Show requirement match matrix and score breakdown.
8. Generate optional premium-positioned artifacts one by one.
9. Save analysis to history.
10. Open extension on a job page and match against a saved resume.

## Current Launch Decision

Status: MVP is locally functional and close to deploy-ready.

Not yet public-launch complete because real staging deployment, production smoke checks, and real job-site extension validation are still manual required steps.
