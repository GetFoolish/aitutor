# TODOS

## Security

### ~~LazyTeachingAssistant race condition on concurrent first requests~~ (FIXED v0.1.3.0)
**Priority:** P1
**Source:** Adversarial review (ship v0.1.1.0)
`services/TeachingAssistant/api.py` — Fixed: added `threading.Lock` with double-checked locking to `LazyTeachingAssistant.get()`.

### ~~WebSocket accepts connection before auth — DoS risk~~ (FIXED v0.1.3.0)
**Priority:** P1
**Source:** Adversarial review (ship v0.1.1.0)
`services/TeachingAssistant/api.py` — Fixed: moved `websocket.accept()` inside `authenticate_observer_websocket()` after the pre-flight check, so unauthenticated clients are rejected without holding an open connection.

### FRONTEND_URL allowlist check for redirect
**Priority:** P2
**Source:** Adversarial review (ship v0.1.1.0)
`services/AuthService/auth_api.py:build_frontend_redirect` — FRONTEND_URL taken from env with no validation. Add hard-coded allowlist check before redirecting auth tokens.

### Observer WebSocket API key over ws:// in local dev
**Priority:** P2
**Source:** Adversarial review (ship v0.1.1.0)
`services/TeachingAssistant/api.py` — API key sent in plaintext JSON first message. wss:// is enforced in prod by Cloud Run but not in local dev. Update test viewer to enforce wss.

### Gemini token endpoint has no per-user rate limit
**Priority:** P2
**Source:** Adversarial review (ship v0.1.1.0)
`services/AuthService/auth_api.py:get_gemini_token` — authenticated user can call in a tight loop, exhausting Gemini API quota. Add 1-token-per-60s per-user cache.

### DashSystem legacy fallback minimum viable data check
**Priority:** P2
**Source:** Adversarial review (ship v0.1.1.0)
`services/DashSystem/dash_system.py:_load_legacy_question_index` — no minimum threshold check. 1 skill + 1 question would be accepted, causing HTTP 500s when DASH exhausts the tiny question set.

### Deterministic shuffle leaks correct answer position
**Priority:** P2
**Source:** Adversarial review (ship v0.1.1.0)
`services/DashSystem/dash_api.py:_build_legacy_radio_choices` — `random.Random(question_id).shuffle()` is deterministic per question_id. Include session-specific component in seed (user_id + question_id + session_id).

### CI JWT test environment uses empty secret
**Priority:** P3
**Source:** Adversarial review (ship v0.1.1.0)
`shared/jwt_config.py` + `.github/workflows/deploy-production.yml` — CI validate job doesn't inject JWT_SECRET; tests run with empty secret and tokens are trivially forgeable in CI. Consider injecting a dummy strong JWT_SECRET in CI for auth tests to be meaningful.

### MONGODB_URI scoped in GH Actions env
**Priority:** P3
**Source:** Adversarial review (ship v0.1.1.0)
`deploy-production.yml` — MONGODB_URI echoed into $GITHUB_ENV and available to all steps in the job. Consider using GCP Secret Manager volume mounts instead.

### check_security_contract.py uses text-matching not structural YAML parse
**Priority:** P3
**Source:** Adversarial review (ship v0.1.1.0)
`scripts/check_security_contract.py` — substring matching on YAML files can be bypassed by comments or indentation changes. Replace with pyyaml structural parse if used as a production gate.

### ~~OAuth state value exposed in JSON response body~~ (FIXED v0.1.3.0)
**Priority:** P2
**Source:** Adversarial review (ship v0.1.2.0)
`services/AuthService/auth_api.py` — Fixed: removed `state` from the `/auth/google` JSON response body. State is only stored in the httpOnly cookie.

### ~~JWT auth token visible to browser extensions during async fetch window~~ (FIXED v0.1.3.0)
**Priority:** P2
**Source:** Adversarial review (ship v0.1.2.0)
`frontend/src/components/auth/GoogleSignIn.tsx` — Fixed: `replaceState` is now called synchronously before the async `/auth/me` fetch, preventing browser extensions from reading the token.

### No PKCE on Google OAuth flow
**Priority:** P2
**Source:** Adversarial review (ship v0.1.2.0)
`services/AuthService/oauth_handler.py` — OAuth flow does not use PKCE (`code_challenge_method` not specified in authlib `AsyncOAuth2Client`). Without PKCE, an intercepted authorization code (e.g., from server logs of the callback URL) could be replayed if redirect_uri checks are bypassed. Add `code_challenge_method="S256"` to the authorization URL generation.

### ~~Dev test button guard uses process.env.NODE_ENV~~ (FIXED v0.1.3.0)
**Priority:** P3
**Source:** Adversarial review (ship v0.1.2.0)
`frontend/src/components/auth/GoogleSignIn.tsx` — Fixed: switched from `process.env.NODE_ENV === 'development'` to `import.meta.env.DEV` for reliable Vite tree-shaking.

## Completed

<!-- completed items go here with version and date -->
