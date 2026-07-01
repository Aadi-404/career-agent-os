# Phase 5 Production Readiness

Phase 5 turns Career Agent OS from a local prototype into a deployable product slice.

## Completed in Phase 5

- Extension Setup screen in the web app.
- Extension readiness diagnostics endpoint.
- Server-issued extension session tokens.
- Token-based extension bootstrap and matching.
- Optional artifact usage tracking.
- Saved opportunity paid actions wired to separated optional endpoints.
- Configurable CORS via `CORS_ALLOW_ORIGINS`.
- `/ready` deployment readiness endpoint.
- Dockerfiles for backend and frontend.
- Local `docker-compose.yml` with PostgreSQL, API, and frontend.

## Runtime Checks

Backend:

```text
GET /health
GET /ready
GET /diagnostics/production-readiness
POST /extension/diagnostics
```

Frontend:

```text
Task 5 -> Extension Setup -> Check Extension Readiness
```

## Extension Validation Checklist

Load the unpacked extension from:

```text
C:\Code\AI\career-agent-os\extension
```

Test pages:

- LinkedIn job detail page
- Naukri job detail page
- Indeed job detail page
- One company careers page

For each page verify:

- Title is extracted.
- Company is extracted.
- Location is extracted.
- JD text is complete enough for scoring.
- Manual JD fallback works when extraction is weak.
- Match saves a job opportunity under the connected user.
- Saved opportunity appears in the web app History tab.

## Production Deployment Checklist

- Set `ENVIRONMENT=production`.
- Set `DATABASE_URL` to managed PostgreSQL.
- Set `CORS_ALLOW_ORIGINS` to the deployed frontend origin only.
- Set `REQUIRE_USER_AUTH=true`.
- Set `ADMIN_USER_IDS` to the first admin user's id.
- Set provider keys only in backend environment variables.
- Set frontend `VITE_API_BASE_URL` to the deployed backend URL before building.
- Run backend `/ready` after deploy.
- Run backend `/diagnostics/production-readiness` and clear all `fail` checks.
- Create a user and save at least one resume before extension testing.

## Environment Profiles

Copy the matching template into the hosting provider's environment variable screen:

```text
deployment/env/backend.local.env.example
deployment/env/backend.staging.env.example
deployment/env/backend.production.env.example
deployment/env/compose.production.env.example
deployment/env/frontend.local.env.example
deployment/env/frontend.staging.env.example
deployment/env/frontend.production.env.example
```

Local keeps `LLM_MODE=mock` and `REQUIRE_USER_AUTH=false` for fast development. Staging and production should use `LLM_MODE=live`, `REQUIRE_USER_AUTH=true`, a managed PostgreSQL `DATABASE_URL`, and deployed CORS origins.

## Deployment Runbook

1. Provision PostgreSQL and create the `careerAgentOS` database.
2. Deploy the backend with the production backend env profile.
3. Confirm backend health:

```text
GET https://api.your-domain.com/health
GET https://api.your-domain.com/ready
GET https://api.your-domain.com/diagnostics/production-readiness
```

4. Deploy the frontend with `VITE_API_BASE_URL` pointing to the backend URL.
5. Open the frontend, claim the local web session, and confirm the Settings readiness panel has no failed checks.
6. Upload or paste one resume, parse it, review/edit normalized resume and JD, then run the free score step.
7. Save the resume and analysis, then verify History shows the saved records.
8. Load the unpacked extension or packaged extension build, connect it to the same user, parse a real job page, and run a match against a saved resume.

## Automated Smoke Check

Run the smoke checker after local startup, Docker Compose startup, staging deploy, or production deploy:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api http://localhost:8000 --frontend http://localhost:5173
```

For Docker Compose:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api http://localhost:8001 --frontend http://localhost:8080
```

For production:

```powershell
python deployment/smoke_check.py --api https://api.your-domain.com --frontend https://app.your-domain.com --strict-production
```

If `REQUIRE_USER_AUTH=true` and you want user-scoped readiness, pass:

```powershell
python deployment/smoke_check.py --api https://api.your-domain.com --user-id your-user-id --session-token your-session-token --strict-production
```

## Production Docker Compose

Use the production compose example when deploying all three services on one host:

```powershell
copy deployment\env\compose.production.env.example deployment\env\compose.production.env
```

Edit `deployment/env/compose.production.env`, then run:

```powershell
docker compose --env-file deployment/env/compose.production.env -f docker-compose.production.example.yml up --build -d
```

Then run:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api http://localhost:8000 --frontend http://localhost:8080 --strict-production
```

For managed PostgreSQL, keep the same backend and frontend services but set `DATABASE_URL` in the host environment or provider secret store instead of using the bundled `postgres` service.

## Extension Release Packaging

Package the extension with the backend API URL that the browser should call:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\package_extension.py --api https://api.your-domain.com --version 0.1.0
```

The script writes:

```text
deployment/releases/extension/<api-host>-v<version>
deployment/releases/extension/<api-host>-v<version>.zip
```

Release checklist:

- Confirm backend `/diagnostics/production-readiness` has no failed checks.
- Package the extension with the deployed backend API URL.
- Load the unpacked release folder in Chrome/Edge developer mode.
- Connect a user and confirm saved resumes load.
- Test LinkedIn, Naukri, Indeed, and one company careers page.
- Use manual JD fallback when auto parsing is weak.
- Save parser feedback from the popup.
- Match a saved resume and confirm the opportunity appears in History.
- Upload the generated zip to the browser extension store only after the real-page checks pass.

## Smoke Test Matrix

| Area | Test | Expected result |
| --- | --- | --- |
| Backend | `/health` | `{"status":"ok"}` |
| Backend | `/ready` | Database initializes and returns `status=ready` |
| Backend | `/diagnostics/production-readiness` | No `fail` checks before public launch |
| Frontend | Settings task | Diagnostics, readiness, users, and scoring settings load |
| Matching | Resume/JD score | Score response returns without generating optional paid artifacts |
| History | Save resume/analysis | Saved records appear under the same user |
| Preparation | Generate plan | Optional plan is generated only when requested |
| Extension | Parse job page | Title, company, location, and JD are detected or manual fallback works |
| Extension | Match saved resume | Opportunity is saved and visible in History |

## Known Remaining Manual Work

Real job-site DOM validation cannot be fully automated from the repo because LinkedIn/Naukri/Indeed often require login, location, account state, or bot protections. The extension now has diagnostics and fallback behavior, but selectors should still be tuned after manual page testing.
