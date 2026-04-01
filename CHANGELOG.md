# Changelog

All notable changes to AI Tutor are documented here.

## [0.1.2.0] - 2026-03-28

### Security
- JWT fail-closed logic now treats any non-explicit-dev `ENVIRONMENT` value as production, preventing ephemeral secrets on misconfigured servers (`prod`, `live`, `staging2`)
- Multi-worker deployments no longer generate per-process ephemeral JWT secrets that invalidate each other's tokens
- Removed `"null"` from default CORS allowed origins — the null origin enables credentialed requests from sandboxed iframes on attacker-controlled pages

## [0.1.1.0] - 2026-03-28

### Added
- MetaMathQA dataset ingestion script (`scripts/ingest_metamathqa.py`) supporting ~395K math problems from HuggingFace

### Changed
- `ingest_gsm8k.py` switched from OpenAI to OpenRouter free model for cost reduction
- Vitest config excludes vendored Perseus tests and pre-existing legacy App.test.tsx; only project smoke tests run

### Fixed
- OAuth state cookie now cleared on all error paths in `/auth/callback` (prevents retry loops after OAuth errors)
- Auth token URL fragment fallback to query params removed; tokens exclusively come from hash fragment (prevents Referer leakage regression)
- JWT config uses ephemeral strong secret in dev when configured secret is weak/missing (prevents trivially forgeable tokens)
- Answer submission shows warning toast when no active session (no silent failure)

## [0.1.0.0] - 2026-03-28

### Added
- Auth token separation: setup tokens and auth JWTs are now distinct types; `POST /auth/complete-setup` rejects normal auth JWTs and vice versa
- Ephemeral Gemini token endpoint (`GET /auth/gemini-token`) issues short-lived tokens instead of exposing raw API keys
- Observer API key protection for TeachingAssistant privileged endpoints (`POST /session/instruction/admin`)
- Bootstrap workflow: `cloudbuild.bootstrap.yaml` for first-deploy DB initialization and seed data loading
- Seed data scripts: `scripts/seed_runtime_data.py` and `scripts/verify_seed_data.py` for DASH skill/question seeding
- Security contract checker: `scripts/check_security_contract.py` validates JWT secrets, API key exposure, and CORS policy
- Comprehensive test suite: 175 backend tests across auth, DASH, TeachingAssistant, shared utils, and bootstrap contracts
- Frontend smoke tests: `frontend/src/smoke/auth-tutor.smoke.test.ts` covering auth+tutor boot path
- Vitest config: `frontend/vitest.config.ts` for frontend unit testing
- Deploy documentation: `documentation/DEPLOYMENT.md` covering staging/production deploy flows
- Legacy DASH MongoDB fallback for compatibility mode with 30 skills and 71 questions

### Changed
- JWT utilities hardened: `shared/jwt_config.py` now fail-closes on missing secrets in production; `services/AuthService/jwt_utils.py` cleanly separates setup vs auth token creation and verification
- `run_tutor.sh` refactored for cleaner service startup with health checks
- `deploy.sh` scoped to deploy-only operations (bootstrap moved to `cloudbuild.bootstrap.yaml`)
- `setup-local-env.sh` updated for accurate local environment setup
- GitHub Actions workflows (`deploy-production.yml`, `deploy-staging.yml`) hardened with pre-deploy gates and secret scoping
- `docker-compose.yml` updated for service parity with production
- `cloudbuild.yaml` restructured for reliable CI/CD deploy flow
- README.md trimmed from 1161 lines to essential content; full deploy docs moved to `documentation/DEPLOYMENT.md`
- DashSystem API and system modules updated for DASH legacy fallback support
- TeachingAssistant API updated with observer endpoint authentication

### Fixed
- `/auth/complete-setup` previously accepted any valid JWT; now correctly rejects non-setup tokens
- JWT fail-closed behavior was inactive in deployed services because `ENVIRONMENT` was never set in CI; now enforced correctly
- First-deploy bootstrap was self-blocking (verify_seed_data ran before data existed); fixed with dedicated bootstrap stage
- Backend coverage gate restored to 50% minimum after it was incorrectly lowered to 20%
