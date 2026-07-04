# Career Agent OS Staging Deployment Runbook

Use this runbook before public production deployment. Staging should be close to production, but it can use test domains, test billing links, and non-sensitive demo data.

The same manual launch checks are also trackable inside:

```text
Scoring Settings -> Launch -> Manual Launch Tracker
```

## 1. Staging Targets

Recommended staging services:

- Backend API: `https://staging-api.your-domain.com`
- Frontend app: `https://staging-career.your-domain.com`
- PostgreSQL database: managed PostgreSQL or a dedicated staging database named `careerAgentOS_staging`
- Extension package: built against the staging API and web URL

Do not reuse your local `careerAgentOS` database for staging.

## 2. Backend Environment

Start from:

```text
deployment/env/backend.staging.env.example
```

Required staging values:

```text
ENVIRONMENT=staging
DATABASE_URL=postgresql://...
CORS_ALLOW_ORIGINS=https://staging-career.your-domain.com
REQUIRE_USER_AUTH=true
ADMIN_USER_IDS=staging-admin
BILLING_WEBHOOK_SECRET=<staging-secret>
LLM_MODE=mock
EMBEDDING_PROVIDER=local
JD_PARSER_MODE=auto
LOG_LEVEL=INFO
```

Use `LLM_MODE=mock` for first staging deployment. Switch to `LLM_MODE=live` only after auth, history, extension, and smoke checks pass.

## 3. Frontend Environment

Start from:

```text
deployment/env/frontend.staging.env.example
```

Required value:

```text
VITE_API_BASE_URL=https://staging-api.your-domain.com
```

Build the frontend only after this value points to the staging backend.

## 4. First Admin Bootstrap

Set:

```text
ADMIN_USER_IDS=staging-admin
```

Then register or login in the web app with:

```text
User ID: staging-admin
Email: your-admin-email@example.com
```

The backend promotes any user id listed in `ADMIN_USER_IDS` to admin during session claim/register/update.

Verify in the app:

- Profile panel shows `admin`.
- Settings allows scoring calibration save/restore controls.
- Known users panel loads.
- Production readiness panel loads.

## 5. Pre-Deploy Local Checks

Run:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\production_rehearsal.py --api https://staging-api.your-domain.com --web https://staging-career.your-domain.com
cd ai-service
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall app
cd ..\frontend
npm run build
```

If Docker is installed locally, also run:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\production_rehearsal.py --api https://staging-api.your-domain.com --web https://staging-career.your-domain.com --compose-config
```

## 6. Deploy Order

1. Provision staging PostgreSQL.
2. Deploy backend with staging env values.
3. Open:

```text
GET https://staging-api.your-domain.com/health
GET https://staging-api.your-domain.com/ready
GET https://staging-api.your-domain.com/diagnostics/production-readiness
```

4. Deploy frontend with staging API URL.
5. Register the first admin user.
6. Run the smoke checker with the admin session token.

## 7. Post-Deploy Smoke Check

After login, copy the user id and session token from your app state or use the backend login endpoint to obtain a token.

Run:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api https://staging-api.your-domain.com --frontend https://staging-career.your-domain.com --user-id staging-admin --session-token <session-token> --billing-webhook-secret <staging-secret> --check-extension-package --strict-production
```

Expected:

- `/health` passes.
- `/ready` passes.
- Readiness has no failed checks.
- Quota API passes.
- Checkout handoff passes, even if manual placeholder.
- Billing webhook mapping passes with staging secret.
- Extension package rehearsal passes.

## 8. Seed Demo Data

For staging demos, seed a dedicated demo user:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\seed_demo_data.py --reset --premium --print-token
```

Or use the web app:

```text
Scoring Settings -> Demo -> Seed Demo Data
```

The web action calls `POST /admin/demo/seed`, requires an admin session when `REQUIRE_USER_AUTH=true`, and switches the browser session to the seeded demo user.

Default login:

```text
User ID: demo-aditya
Password: DemoPass123!
```

Seeded data includes:

- Two saved resumes.
- Two saved JDs.
- One saved analysis.
- One saved comparison run.
- One preparation session with progress.
- Two job opportunities in the application pipeline.
- One extension validation record.
- One score feedback label.
- Usage events for quota/dashboard testing.

Use the demo account to show:

1. History dashboard.
2. Saved resume/JD reuse.
3. Saved comparison.
4. Prep progress tracking.
5. Extension validation records.
6. Score evaluation signals.

## 9. Extension Staging Package

Build:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\package_extension.py --api https://staging-api.your-domain.com --web https://staging-career.your-domain.com --version 0.1.0-staging
```

Load the generated unpacked folder from:

```text
deployment/releases/extension/staging-api.your-domain.com-v0.1.0-staging
```

Validate:

- Login/register works.
- Saved resumes load.
- LinkedIn/Naukri/Indeed/company career pages parse title/company/JD where possible.
- Manual JD paste fallback works.
- Match saves a job opportunity.
- Saved opportunity appears in web History.

## 10. Switch Staging To Live AI

Only after the mock-mode flow passes:

```text
LLM_MODE=live
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=<staging-or-real-key>
EMBEDDING_PROVIDER=auto
```

Then rerun one score and one optional artifact at a time:

1. Score.
2. Preparation plan.
3. Gap report.
4. Interview questions.
5. Cross-questions.

This validates the modular call split and prevents a single heavy LLM call from hiding cost or quota issues.

## 11. Rollback And Data Safety

Before schema or deployment changes:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\backup_database.py --pretty
```

For staging restore testing only:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\restore_database.py deployment\backups\career-agent-os-backup.json --yes
```

For production, prefer provider-native PostgreSQL snapshots or point-in-time recovery.

## 12. Exit Criteria

Staging is ready for production planning when:

- Admin login works.
- Free score flow works.
- Optional premium-positioned modules work one by one.
- Saved resumes, JDs, analyses, prep sessions, comparisons, and opportunities persist.
- Extension saved-resume match works with manual JD fallback.
- Usage quota panel updates.
- Settings readiness has no failed checks.
- Smoke checker passes.
- Backup export succeeds.
