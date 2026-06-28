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
- Set provider keys only in backend environment variables.
- Set frontend `VITE_API_BASE_URL` to the deployed backend URL before building.
- Run backend `/ready` after deploy.
- Create a user and save at least one resume before extension testing.

## Known Remaining Manual Work

Real job-site DOM validation cannot be fully automated from the repo because LinkedIn/Naukri/Indeed often require login, location, account state, or bot protections. The extension now has diagnostics and fallback behavior, but selectors should still be tuned after manual page testing.
