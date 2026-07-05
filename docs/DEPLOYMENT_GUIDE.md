# Career Agent OS Deployment Guide

This guide is the single path from local development to staging and production. Use it with `docs/DEPLOYMENT_CHECKLIST.md` for detailed environment values and `docs/STAGING_DEPLOYMENT_RUNBOOK.md` for staging rehearsal.

## 1. Local Development

Start PostgreSQL with database `careerAgentOS`, then configure `ai-service/.env` from the local template.

```powershell
cd C:\Code\AI\career-agent-os\ai-service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd C:\Code\AI\career-agent-os\frontend
npm run dev
```

Local verification:

```powershell
cd C:\Code\AI\career-agent-os
cd ai-service
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall app
cd ..\frontend
npm run build
npm run smoke
```

## 2. Staging

Use staging for the first real multi-user deployment. Keep `LLM_MODE=mock` until auth, history, billing placeholders, extension, and smoke checks pass.

Required staging setup:

- Dedicated PostgreSQL database, not the local `careerAgentOS` database.
- Backend env from `deployment/env/backend.staging.env.example`.
- Frontend env from `deployment/env/frontend.staging.env.example`.
- `REQUIRE_USER_AUTH=true`.
- `ADMIN_USER_IDS=<staging-admin-user-id>`.
- Deployed CORS origin only, no localhost.

Deploy order:

1. Provision PostgreSQL.
2. Deploy backend.
3. Open `/health`, `/ready`, and `/diagnostics/production-readiness`.
4. Deploy frontend with `VITE_API_BASE_URL` pointing to staging backend.
5. Register or login as the first admin user.
6. Open Settings and run `Run Production Smoke`.
7. Run CLI smoke:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api https://staging-api.your-domain.com --frontend https://staging-career.your-domain.com --user-id staging-admin --session-token <session-token> --billing-webhook-secret <staging-secret> --check-extension-package --strict-production
```

## 3. Production

Production requires all Settings readiness checks to be clear or intentionally accepted.

Required production values:

- `ENVIRONMENT=production`
- `REQUIRE_USER_AUTH=true`
- `DATABASE_URL=postgresql://...`
- `CORS_ALLOW_ORIGINS=https://app.your-domain.com`
- `ADMIN_USER_IDS=<first-admin-user-id>`
- `BILLING_CHECKOUT_PROVIDER=stripe|razorpay|paddle`
- `BILLING_CHECKOUT_URL=https://...`
- `BILLING_CHECKOUT_SUCCESS_URL=https://app.your-domain.com/...`
- `BILLING_CHECKOUT_CANCEL_URL=https://app.your-domain.com/...`
- `BILLING_WEBHOOK_SECRET=<strong-secret>`
- `LLM_MODE=live` only after mock smoke passes
- Provider key for Groq, OpenAI, or Gemini
- `EMBEDDING_PROVIDER=auto`
- `LOG_LEVEL=INFO`

Production deploy order:

1. Export or snapshot the staging database if needed.
2. Create production PostgreSQL.
3. Deploy backend with production env values.
4. Deploy frontend with production API URL.
5. Register/login the first admin.
6. Open Settings -> Production Readiness.
7. Run Settings -> Deployment Runbook -> `Run Production Smoke`.
8. Run CLI smoke with `--strict-production`.
9. Package the browser extension against production URLs.
10. Run one free score-only match and one optional premium artifact.

## 4. Demo Data Safety

Use demo data only for project reviews.

Seed from the app:

```text
Settings -> Demo -> Seed Demo Data
```

Clean from the app before public production demos:

```text
Settings -> Demo -> Clean Demo Data
```

The cleanup action calls `POST /admin/demo/cleanup`, deletes only the configured demo user workspace, and removes demo usage events before deleting the demo user.

## 5. Extension Release

Package the extension for the deployed backend and frontend:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\package_extension.py --api https://api.your-domain.com --web https://app.your-domain.com --version 0.1.0
```

Manual validation:

- Login/register in the extension.
- Load saved resumes.
- Parse LinkedIn, Naukri, Indeed, and one company careers page.
- Use manual JD paste when auto-parse is incomplete.
- Match a saved resume.
- Confirm the opportunity appears in web History.

## 6. Release Gate

Do not call the release ready until all are true:

- Backend tests pass.
- Frontend build and smoke pass.
- Settings production readiness has no failed checks.
- In-app production smoke passes.
- CLI smoke passes with `--strict-production`.
- Extension package validates.
- Demo data is cleaned unless this is a private portfolio demo.
