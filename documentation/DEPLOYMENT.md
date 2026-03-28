# Deployment

## Overview

The deploy path is:

1. GitHub Actions validates backend, frontend, security, and seed-data gates.
2. `deploy.sh` resolves existing Cloud Run service URLs.
3. If backend services do not exist yet, `deploy.sh` runs `cloudbuild.bootstrap.yaml`.
4. `deploy.sh` reruns the full `cloudbuild.yaml` with resolved public URLs.
5. Cloud Run services receive runtime secrets through Secret Manager bindings via `--set-secrets`.

## Required Secret Manager Secrets

These names are the defaults used by the workflows and `deploy.sh`:

- `MONGODB_URI`
- `OPENROUTER_API_KEY`
- `GEMINI_API_KEY`
- `JWT_SECRET`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `OBSERVER_API_KEY`

The workflows pass them to Cloud Build as secret references in the form `<SECRET_NAME>:latest`.

## Required Non-Secret Config

- `MONGODB_DB_NAME`
- `FRONTEND_URL`
- `ALLOWED_ORIGINS`
- `GOOGLE_CLIENT_ID_PUBLIC`
- `GEMINI_MODEL` (optional, defaults in script/config)

`GOOGLE_CLIENT_ID_PUBLIC` is used only for the frontend build arg.

## Manual Deploy

```bash
export MONGODB_DB_NAME=ai_tutor
export MONGODB_URI_SECRET=MONGODB_URI:latest
export OPENROUTER_API_KEY_SECRET=OPENROUTER_API_KEY:latest
export GEMINI_API_KEY_SECRET=GEMINI_API_KEY:latest
export JWT_SECRET_SECRET=JWT_SECRET:latest
export GOOGLE_CLIENT_ID_SECRET=GOOGLE_CLIENT_ID:latest
export GOOGLE_CLIENT_SECRET_SECRET=GOOGLE_CLIENT_SECRET:latest
export OBSERVER_API_KEY_SECRET=OBSERVER_API_KEY:latest
export GOOGLE_CLIENT_ID_PUBLIC="$(gcloud secrets versions access latest --secret=GOOGLE_CLIENT_ID)"
export FRONTEND_URL=https://staging.teachr.live
export ALLOWED_ORIGINS=https://staging.teachr.live

./deploy.sh staging
```

For production, change `FRONTEND_URL`, `ALLOWED_ORIGINS`, and run `./deploy.sh prod`.

## Validation Gates

The deploy workflows block on:

```bash
python3 -m pytest
python3 scripts/check_security_contract.py
python3 scripts/verify_seed_data.py
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run build
cd frontend && npm run test:ci
```

## Notes

- `cloudbuild.bootstrap.yaml` is only for first-time environments where service URLs do not exist yet.
- `cloudbuild.yaml` is the steady-state deploy path.
- `OBSERVER_API_KEY` must be configured; observer/admin endpoints stay disabled otherwise.
