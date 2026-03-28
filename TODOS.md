# TODOS

## Security

### LazyTeachingAssistant race condition on concurrent first requests
**Priority:** P1
**Source:** Adversarial review (ship v0.1.1.0)
`services/TeachingAssistant/api.py` — `LazyTeachingAssistant.get()` is not thread-safe. Multiple concurrent Cloud Run requests can each instantiate `TeachingAssistant()`, creating duplicate MongoDB-backed state. Fix: use a threading lock or module-level singleton at startup.

### WebSocket accepts connection before auth — DoS risk
**Priority:** P1
**Source:** Adversarial review (ship v0.1.1.0)
`services/TeachingAssistant/api.py:~798` — `await websocket.accept()` called before `authenticate_observer_websocket()`. Any unauthenticated client holds the connection open for 5s per attempt. Fix: move accept into the auth function after successful verification.

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

## Completed

<!-- completed items go here with version and date -->
