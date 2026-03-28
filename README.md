# AI Tutor

AI Tutor is a multi-service tutoring app with a React frontend and four shipped backend services:

- `frontend/`: student UI and direct Gemini Live tutor client
- `services/AuthService/`: Google OAuth, JWT auth, Gemini ephemeral token broker
- `services/DashSystem/`: adaptive question selection and skill scoring
- `services/SherlockEDApi/`: question rendering support APIs
- `services/TeachingAssistant/`: session orchestration, feed processing, observer/admin tooling

`services/Tutor/` is legacy reference code. It is not part of the supported runtime path and is not started by local bootstrap, Docker Compose, or deploy.

## Supported Architecture

The supported tutor flow is:

1. Frontend authenticates through `AuthService`.
2. Frontend requests a single-use Gemini token from `GET /auth/gemini-token`.
3. Frontend connects directly to Gemini Live with that ephemeral token.
4. Frontend fetches questions and submits answers through `DashSystem`.
5. Frontend exchanges session/feed/instruction traffic with `TeachingAssistant`.

The raw Gemini API key is intentionally not exposed to frontend clients.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 22+
- MongoDB with seeded `generated_skills` and `scraped_questions`
- Google OAuth credentials
- Google Gemini API key
- OpenRouter API key

### 1. Create the virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt -r requirements-test.txt
cd frontend
npm install
cd ..
```

### 3. Generate the local env contract

```bash
./setup-local-env.sh
```

That creates `.env` from `.env.example`, generates local `JWT_SECRET` and `OBSERVER_API_KEY` values, and leaves placeholders for the external credentials you must fill in.

### 4. Review `.env`

Minimum required variables:

```dotenv
MONGODB_URI=...
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...
JWT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
OBSERVER_API_KEY=...
```

Local service URLs default to:

```dotenv
FRONTEND_URL=http://localhost:3000
AUTH_SERVICE_URL=http://localhost:8003
DASH_API_URL=http://localhost:8000
SHERLOCKED_API_URL=http://localhost:8001
TEACHING_ASSISTANT_API_URL=http://localhost:8002
ALLOWED_ORIGINS=http://localhost:3000
```

### 5. Start the app

```bash
./run_tutor.sh
```

That starts:

- frontend on `http://localhost:3000`
- DASH API on `http://localhost:8000`
- SherlockED API on `http://localhost:8001`
- TeachingAssistant API on `http://localhost:8002`
- Auth Service on `http://localhost:8003`

## Docker Compose

`docker-compose.yml` mirrors the supported shipped architecture:

- `mongodb`
- `dash-api`
- `sherlocked-api`
- `teaching-assistant`
- `auth-service`
- `frontend`

Run it with:

```bash
docker compose up --build
```

Compose expects the same root `.env` contract. If you want Compose to use a remote Mongo instance instead of the bundled container, set `DOCKER_MONGODB_URI`.
`TeachingAssistant` uses `DOCKER_DASH_API_URL` for its internal server-to-server DASH calls, while the browser-facing frontend still uses `DASH_API_URL`.

## Data Bootstrap

The runtime expects seeded Mongo collections:

- `generated_skills`
- `scraped_questions`

Useful scripts:

- `services/tools/run_all_migrations.py`
- `services/tools/migrate_skills_to_mongodb.py`
- `services/tools/migrate_perseus_to_mongodb.py`
- `services/tools/migrate_dash_questions_to_mongodb.py`
- `scripts/verify_seed_data.py`

Verify the current database before running the app or deploying:

```bash
python3 scripts/verify_seed_data.py
```

## Validation Commands

Backend:

```bash
python3 -m pytest
python3 scripts/check_security_contract.py
python3 scripts/verify_seed_data.py
```

Frontend:

```bash
cd frontend
npm run lint
npm run type-check
npm run build
npm run test:ci
```

`npm run test:ci` is the smoke gate for auth bootstrap plus tutor token boot.

## Observer/Admin Tooling

Observer/admin endpoints in `TeachingAssistant` are disabled unless `OBSERVER_API_KEY` is explicitly configured. The local dev viewer lives at:

`services/TeachingAssistant/scripts/test_channel1_viewer.html`

Paste the configured `OBSERVER_API_KEY` into the page before using it.

## Deployment

Deploys are branch-driven:

- `staging` branch -> staging workflow
- `main` branch -> production workflow

Both GitHub workflows:

1. run backend tests
2. run the security contract check
3. verify Mongo seed data
4. run frontend lint, type-check, build, and smoke tests
5. deploy only after validation passes

Runtime secrets are bound through Google Secret Manager in Cloud Run via `--set-secrets`. The deploy script supports first-time environments by bootstrapping backend services first and then redeploying with resolved service URLs.

See [documentation/DEPLOYMENT.md](documentation/DEPLOYMENT.md) for the deploy contract and required Secret Manager names.

## Legacy Notes

- `services/Tutor/` is legacy and intentionally not started.
- `/auth/gemini-key` is intentionally absent. Use `/auth/gemini-token`.
- `cloudbuild.bootstrap.yaml` exists only to bootstrap missing Cloud Run services before the normal deploy pass.
