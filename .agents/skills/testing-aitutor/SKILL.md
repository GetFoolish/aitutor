# Testing AITutor

## Backend Tests

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

- 159+ tests, minimum 50% coverage required
- Tests use monkeypatching extensively — no real MongoDB or external services needed
- `PYTHONPATH=.` is required since the repo uses relative imports from root

## Frontend Checks

```bash
cd frontend
npx tsc --noEmit          # TypeScript type check
NODE_OPTIONS="--max-old-space-size=4096" npx vite build  # Production build
```

- **Important:** The frontend production build may OOM with default Node heap. Use `--max-old-space-size=4096`.
- Build output goes to `frontend/build/`

## Targeted Testing Strategies

### Concurrency / Race Conditions
Use `threading.Barrier` + mock constructors to test thread-safety:
```python
import threading
barrier = threading.Barrier(N)
def worker():
    barrier.wait()  # All threads start simultaneously
    result = thing_under_test()
```
Mock the constructor to count instantiations and add small delays to widen race windows.

### WebSocket Endpoints
Use `fastapi.testclient.TestClient` with `client.websocket_connect()`:
- Monkeypatch `teaching_api.ta` with a `SimpleNamespace` containing a `DummySessionManager`
- Set/unset `OBSERVER_API_KEY` env var to test auth scenarios
- `WebSocketDisconnect` may be raised during connect (not just receive) if server closes before accepting

### Auth/OAuth Endpoints
Use `fastapi.testclient.TestClient`:
- Monkeypatch `oauth_handler.get_authorization_url` to return test URLs
- Check response body, cookies, and status codes
- No real Google OAuth credentials needed for unit-level testing

## Common Pitfalls

- The `TeachingAssistant()` constructor requires MongoDB (`MONGODB_URI`). Mock it when testing `LazyTeachingAssistant` or API endpoints.
- `OBSERVER_API_KEY` defaults to an insecure value that is rejected in non-dev environments. Set a custom value for testing observer endpoints.
- Frontend uses Vite — use `import.meta.env.DEV` (not `process.env.NODE_ENV`) for dev-only guards.
- The repo has no CI configured on GitHub. Run tests locally before pushing.

## Devin Secrets Needed

No secrets required for local testing. MongoDB and Google OAuth credentials would be needed for full end-to-end testing.
