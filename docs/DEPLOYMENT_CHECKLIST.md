# Career Agent OS Deployment Checklist

Use this before deploying staging or production. The app is split into a FastAPI backend, Vite frontend, PostgreSQL database, and optional browser extension.

## Required Backend Environment

- `ENVIRONMENT=production` for public deployment.
- `DATABASE_URL=postgresql://...` for managed PostgreSQL, or `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- `CORS_ALLOW_ORIGINS=https://app.your-domain.com` with no localhost origin in production.
- `REQUIRE_USER_AUTH=true`.
- `ADMIN_USER_IDS=<first-admin-user-id>`.
- `BILLING_WEBHOOK_SECRET=<strong-random-secret>`.
- `LLM_MODE=live` when optional AI artifacts should call a real provider.
- One provider key: `GROQ_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or generic `LLM_API_KEY`.
- `EMBEDDING_PROVIDER=auto` for provider-backed semantic matching with local fallback.
- `JD_PARSER_MODE=auto` for deterministic parsing with LLM assist when configured.
- `LOG_LEVEL=INFO`.

## Required Frontend Environment

- `VITE_API_BASE_URL=https://api.your-domain.com`.

## Billing Webhook Contract

Send provider webhooks to:

```text
POST /billing/webhooks/subscription
X-Billing-Webhook-Secret: <BILLING_WEBHOOK_SECRET>
```

The endpoint accepts normalized app payloads and native `stripe`, `razorpay`, or `paddle` subscription payloads through `providerPayload`. For native payloads, set the app user id in provider metadata:

- Stripe: `data.object.metadata.userId`
- Razorpay: `payload.subscription.entity.notes.user_id`
- Paddle: `data.custom_data.userId`

## Pre-Deploy Verification

Run locally before shipping:

```powershell
cd frontend
npm run build
cd ..\ai-service
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall app
```

## Post-Deploy Smoke Check

Check backend:

```text
GET https://api.your-domain.com/health
GET https://api.your-domain.com/ready
GET https://api.your-domain.com/diagnostics/production-readiness
```

Run the smoke checker:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api https://api.your-domain.com --frontend https://app.your-domain.com
```

Run user-scoped comparison and billing smoke checks after creating a test user:

```powershell
.\ai-service\.venv\Scripts\python.exe deployment\smoke_check.py --api https://api.your-domain.com --frontend https://app.your-domain.com --user-id your-user-id --session-token your-session-token --billing-webhook-secret your-webhook-secret
```

## Manual Product Smoke

- Register or claim the first admin user from `ADMIN_USER_IDS`.
- Confirm Settings shows production readiness with no failed checks.
- Save one resume in the library.
- Save one JD in the library.
- Run the free score step.
- Build optional premium artifacts only after score succeeds.
- Run a saved comparison and confirm it appears in Recent Runs and History.
- Rename and delete one saved comparison.
- Package the extension with the deployed API URL and verify manual JD fallback.
