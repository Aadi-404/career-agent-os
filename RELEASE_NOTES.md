# Career Agent OS MVP Release Notes

## Release Position

Career Agent OS is a locally verified MVP for resume-to-JD scoring, saved career workspace history, preparation planning, and browser-extension assisted job matching.

Status: staging-ready after hosted environment values and secrets are configured.

## MVP Capabilities

- Resume upload/extraction for TXT, PDF, and DOCX.
- Structured resume normalization with review/edit before scoring.
- JD parsing with dynamic requirement extraction.
- Explainable score-only resume/JD matching.
- Requirement Match Matrix with semantic evidence matching.
- Shortlisting, interview-readiness, and opportunity scores.
- Optional premium-positioned artifacts generated one at a time:
  - preparation plan
  - gap report
  - interview questions
  - cross-questions
  - resume improvements
- PostgreSQL persistence for users, resumes, JDs, analyses, comparisons, prep sessions, opportunities, research notes, feedback, and usage.
- Password auth, session tokens, user-scoped APIs, and admin guards.
- Browser extension with saved-resume matching, job-page parsing, manual JD fallback, login/register, and parser feedback.
- Research notes, apply decisioning, evidence-constrained resume rewrite, and Career Agent planner groundwork.
- Settings release dashboard with readiness, smoke, demo-data, extension package, and validation status.

## AI And Cost-Control Design

The product rule is:

```text
Algorithm calculates. LLM explains and coaches.
```

Mandatory matching uses a score-only path. Preparation, questions, rewrite, and other coaching artifacts are split into separate endpoints so they can be called only when needed.

Semantic matching uses provider-backed embeddings when configured and local fallback when offline or in mock mode.

## Verified Local Gates

Use:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\verify_release.py
```

Main checks covered:

- backend unittest suite
- backend compile check
- deployment script compile check
- extension popup syntax
- extension parser fixtures
- frontend build
- frontend smoke
- production rehearsal

Settings also includes:

- `Run Production Smoke`
- `Refresh Release Summary`
- `Export Launch Evidence`

## Known Launch Limitations

These are not code blockers, but they are required before public production launch:

- Deploy staging backend/frontend with real domains.
- Configure secrets outside git.
- Set production CORS domains.
- Configure billing checkout provider, checkout URL, return URLs, and webhook secret.
- Validate the browser extension on LinkedIn, Naukri, Indeed, and one company careers page.
- Run in-app smoke and CLI smoke against staging/production URLs.
- Collect real labelled resumes/JDs before scoring calibration is treated as tuned.

## Reviewer Demo Path

1. Start backend and frontend locally.
2. Register or login as an admin workspace user.
3. Open Settings -> Demo -> Seed Demo Data.
4. Open Command Center and History.
5. Review the saved score and Requirement Match Matrix.
6. Generate optional artifacts one by one.
7. Open Extension Setup and review parser validation.
8. Open Settings -> Release Readiness Dashboard.
9. Run Production Smoke.
10. Export Launch Evidence.

Default seeded demo:

```text
User ID: demo-aditya
Password: DemoPass123!
```

## Related Docs

- `PROJECT_STATUS.md`
- `docs/MVP_LAUNCH_STATUS.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/DEPLOYMENT_CHECKLIST.md`
- `docs/STAGING_DEPLOYMENT_RUNBOOK.md`
