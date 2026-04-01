import asyncio
import importlib
import logging
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

import services.AuthService.jwt_utils as jwt_utils
import shared.auth_middleware as auth_middleware
import shared.cache_middleware as cache_middleware
import shared.cache_utils as cache_utils
import shared.circuit_breaker as circuit_breaker
import shared.db_utils as db_utils
import shared.field_filter as field_filter
import shared.model_router as model_router
import shared.pagination as pagination
import shared.retry_utils as retry_utils


def make_request(token: str | None = None, path: str = "/", method: str = "GET") -> Request:
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request({"type": "http", "method": method, "path": path, "headers": headers})


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.deleted = []

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def keys(self, pattern):
        prefix = pattern[:-1]
        return [key for key in self.store if key.startswith(prefix)]

    def delete(self, *keys):
        self.deleted.extend(keys)
        for key in keys:
            self.store.pop(key, None)

    def info(self, section):
        return {"keyspace_hits": 3, "keyspace_misses": 1}

    def dbsize(self):
        return len(self.store)


class FakeQueryCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field, direction):
        reverse = direction == -1
        self.items.sort(key=lambda item: item.get(field), reverse=reverse)
        return self

    def limit(self, count):
        self.items = self.items[:count]
        return self

    def __iter__(self):
        return iter(self.items)


class FakeCollection:
    def __init__(self, items):
        self.items = list(items)
        self.query = None

    def find(self, query):
        self.query = query
        filtered = self.items
        for key, value in query.items():
            if isinstance(value, dict) and "$lt" in value:
                filtered = [item for item in filtered if item.get(key) < value["$lt"]]
            elif isinstance(value, dict) and "$gt" in value:
                filtered = [item for item in filtered if item.get(key) > value["$gt"]]
            else:
                filtered = [item for item in filtered if item.get(key) == value]
        return FakeQueryCursor(filtered)


class DemoFilterResponse(field_filter.FilterableResponse):
    user_id: str
    name: str
    email: str


def reload_cors_module(monkeypatch, allowed_origins=None, production_domain=None):
    if allowed_origins is None:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("ALLOWED_ORIGINS", allowed_origins)
    if production_domain is None:
        monkeypatch.delenv("PRODUCTION_DOMAIN", raising=False)
    else:
        monkeypatch.setenv("PRODUCTION_DOMAIN", production_domain)
    import shared.cors_config as cors_config

    return importlib.reload(cors_config)


def reload_jwt_config_module(monkeypatch, *, secret: str, environment: str = "testing", k_service: str | None = None):
    monkeypatch.setenv("JWT_SECRET", secret)
    monkeypatch.setenv("ENVIRONMENT", environment)
    if k_service is None:
        monkeypatch.delenv("K_SERVICE", raising=False)
    else:
        monkeypatch.setenv("K_SERVICE", k_service)
    import shared.jwt_config as jwt_config

    return importlib.reload(jwt_config)


def test_auth_middleware_validates_auth_tokens():
    token = jwt_utils.create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-123",
        }
    )

    request = make_request(token)

    assert auth_middleware.get_current_user(request) == "user-123"
    assert auth_middleware.get_user_from_token(token) == {
        "user_id": "user-123",
        "email": "student@example.com",
        "name": "Student",
        "google_id": "google-123",
    }


def test_auth_middleware_rejects_missing_or_wrong_token_type():
    with pytest.raises(HTTPException) as missing_header:
        auth_middleware.get_current_user(make_request())

    assert missing_header.value.status_code == 401

    setup_token = jwt_utils.create_setup_token(
        {"id": "google-123", "email": "student@example.com", "name": "Student"}
    )
    assert auth_middleware.get_user_from_token(setup_token) is None

    with pytest.raises(HTTPException) as wrong_type:
        auth_middleware.get_current_user(make_request(setup_token))

    assert wrong_type.value.status_code == 401


@pytest.mark.asyncio
async def test_cache_response_uses_cache_and_prefix_keys(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", fake_redis)

    calls = {"count": 0}

    @cache_utils.cache_response(ttl=60, prefix="questions")
    async def load_questions(question_id):
        calls["count"] += 1
        return {"question_id": question_id}

    first = await load_questions("q-1")
    second = await load_questions("q-1")

    key = cache_utils.generate_cache_key("questions", "q-1")
    assert key.startswith("questions:")
    assert first == second == {"question_id": "q-1"}
    assert calls["count"] == 1

    cache_utils.invalidate_cache("questions")
    assert fake_redis.deleted == [key]

    stats = cache_utils.get_cache_stats()
    assert stats["available"] is True
    assert stats["total_keys"] == 0
    assert stats["hit_rate"] == 0.75


def test_cache_utils_handles_unavailable_or_erroring_redis(monkeypatch):
    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", False)
    assert cache_utils.get_cache_stats() == {"available": False}

    class BrokenRedis(FakeRedis):
        def info(self, section):
            raise RuntimeError("boom")

    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", BrokenRedis())
    assert cache_utils.get_cache_stats()["available"] is False


def test_circuit_breaker_opens_recovers_and_reports_state(monkeypatch):
    breaker = circuit_breaker.CircuitBreaker(failure_threshold=1, recovery_timeout=5)
    times = iter([10.0, 12.0, 14.0, 20.0, 20.0])
    monkeypatch.setattr(circuit_breaker.time, "time", lambda: next(times, 30.0))

    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("boom")))

    assert breaker.state == circuit_breaker.CircuitState.OPEN

    with pytest.raises(Exception, match="Circuit breaker OPEN"):
        breaker.call(lambda: "still blocked")

    result = breaker.call(lambda: "ok")
    assert result == "ok"
    assert breaker.get_state()["state"] == circuit_breaker.CircuitState.CLOSED.value


@pytest.mark.asyncio
async def test_circuit_breaker_async_timeout_and_decorator():
    breaker = circuit_breaker.CircuitBreaker(failure_threshold=1, timeout=0.001)

    async def too_slow():
        await asyncio.sleep(0.01)

    with pytest.raises(asyncio.TimeoutError):
        await breaker.call_async(too_slow)

    @circuit_breaker.circuit_breaker(failure_threshold=1, timeout=0.1)
    async def decorated():
        return "ok"

    assert await decorated() == "ok"


def test_cursor_pagination_for_queries_and_lists():
    collection = FakeCollection(
        [
            {"_id": "1", "score": 30},
            {"_id": "2", "score": 20},
            {"_id": "3", "score": 10},
        ]
    )
    page = pagination.paginate_query(collection, {}, limit=2, sort_field="score", sort_descending=True)
    assert [item["_id"] for item in page.items] == ["1", "2"]
    assert page.has_more is True
    assert page.next_cursor is not None

    next_page = pagination.paginate_query(
        collection,
        {},
        cursor=page.next_cursor,
        limit=2,
        sort_field="score",
        sort_descending=True,
    )
    assert [item["_id"] for item in next_page.items] == ["3"]
    assert next_page.has_more is False

    list_page = pagination.paginate_list(["a", "b", "c"], limit=2)
    assert list_page.items == ["a", "b"]
    assert list_page.has_more is True
    assert pagination.paginate_list(["a", "b"], cursor="invalid", limit=1).items == ["a"]


def test_pagination_cursor_decode_rejects_invalid_value():
    with pytest.raises(ValueError):
        pagination.PaginationCursor.decode("not-base64")


def test_retry_with_backoff_and_error_handler(monkeypatch):
    waits = []
    monkeypatch.setattr(retry_utils.time, "sleep", lambda seconds: waits.append(seconds))

    attempts = {"count": 0}
    retries = []

    @retry_utils.retry_with_backoff(
        retries=3,
        backoff_factor=2,
        exceptions=(ValueError,),
        on_retry=lambda attempt, error: retries.append((attempt, str(error))),
    )
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("retry me")
        return "ok"

    assert flaky() == "ok"
    assert waits == [1, 2]
    assert retries == [(0, "retry me"), (1, "retry me")]

    assert retry_utils.safe_execute(lambda: 42) == 42
    assert retry_utils.safe_execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")), default="fallback") == "fallback"

    with retry_utils.ErrorHandler("suppressed"):
        raise RuntimeError("ignore")

    with pytest.raises(RuntimeError):
        with retry_utils.ErrorHandler("reraised", raise_on_error=True):
            raise RuntimeError("boom")


def test_retry_specialized_decorators():
    api_attempts = {"count": 0}

    @retry_utils.retry_on_api_error(retries=2)
    def flaky_api():
        api_attempts["count"] += 1
        if api_attempts["count"] == 1:
            raise retry_utils.RetryableError("retry")
        return "ok"

    assert flaky_api() == "ok"

    assert issubclass(retry_utils.NonRetryableError, Exception)


def test_db_utils_pagination_monitor_and_helper(monkeypatch):
    params = db_utils.PaginationParams(page=0, limit=500, max_limit=50)
    assert params.page == 1
    assert params.limit == 50
    assert params.offset == 0
    assert params.to_dict() == {"page": 1, "limit": 50, "offset": 0}

    response = db_utils.PaginatedResponse(items=[1, 2], total=5, page=1, limit=2)
    assert response.total_pages == 3
    assert response.has_next is True
    assert response.has_prev is False
    assert response.to_dict()["pagination"]["total_pages"] == 3

    monitor = db_utils.QueryMonitor(slow_query_threshold=0.5)
    monkeypatch.setattr(db_utils.time, "time", lambda: 123.0)
    for _ in range(6):
        monitor.monitor_query("load_users", 1.0, {"active": True})
    monitor.monitor_query("fast_query", 0.1)
    assert monitor.get_slow_queries(limit=1)[0]["query_name"] == "load_users"
    assert "load_users" in monitor.get_recommendations()[0]

    paginated = db_utils.paginate(items=["a"], total=1, page=1, limit=10)
    assert paginated.items == ["a"]
    assert "users" in db_utils.INDEX_RECOMMENDATIONS


@pytest.mark.asyncio
async def test_field_filter_helpers_cover_sync_and_async_paths():
    data = {"user_id": "u1", "name": "Ada", "nested": {"email": "ada@example.com", "secret": "x"}}
    assert field_filter.filter_fields(data, fields={"user_id", "nested"}, exclude={"secret"}) == {
        "user_id": "u1",
        "nested": {},
    }
    assert field_filter.filter_fields([data], fields={"name"}) == [{"name": "Ada"}]
    assert field_filter.filter_fields(None) is None
    assert field_filter.parse_fields_query("user_id, name ,,email") == {"user_id", "name", "email"}
    assert field_filter.parse_fields_query(None) is None

    response = DemoFilterResponse(user_id="u1", name="Ada", email="ada@example.com")
    assert response.dict_filtered(fields={"name"}) == {"name": "Ada"}
    assert field_filter.get_field_set("user_minimal") == {"user_id", "name", "current_grade"}
    with pytest.raises(ValueError):
        field_filter.get_field_set("missing")

    @field_filter.filterable_response(default_exclude={"secret"})
    def sync_handler(fields=None, exclude=None):
        return {"name": "Ada", "secret": "x"}

    @field_filter.filterable_response()
    async def async_handler(fields=None, exclude=None):
        return {"name": "Ada", "email": "ada@example.com"}

    assert sync_handler(fields="name") == {"name": "Ada"}
    assert await async_handler(fields="email") == {"email": "ada@example.com"}


def test_model_router_routes_tasks_and_collects_stats():
    router = model_router.ModelRouter()
    assert router.classify_task_complexity("greeting", context_length=10) == model_router.ComplexityTier.SIMPLE
    assert router.classify_task_complexity("grading", context_length=9000) == model_router.ComplexityTier.COMPLEX
    assert router.classify_task_complexity("grading", is_final_assessment=True) == model_router.ComplexityTier.CRITICAL

    config, complexity = router.route_request("greeting", "Hello there")
    assert complexity == model_router.ComplexityTier.SIMPLE
    assert config.provider == "google"
    assert router.estimate_cost(model_router.ModelTier.FAST, input_tokens=500, output_tokens=500) > 0
    assert router.get_stats()["total_calls"] == 1

    _, global_complexity = model_router.route_llm_request("grading", "Explain this", requires_reasoning=True)
    assert global_complexity == model_router.ComplexityTier.COMPLEX
    assert "tier_distribution" in model_router.get_routing_stats()


@pytest.mark.asyncio
async def test_cache_control_middleware_sets_expected_headers():
    middleware = cache_middleware.CacheControlMiddleware(app=lambda scope, receive, send: None)

    async def call_next(_request):
        return Response("ok")

    health_response = await middleware.dispatch(make_request(path="/health"), call_next)
    session_response = await middleware.dispatch(make_request(path="/session/info/123"), call_next)
    user_response = await middleware.dispatch(make_request(path="/auth/me"), call_next)
    asset_response = await middleware.dispatch(make_request(path="/app.js"), call_next)

    assert health_response.headers["Cache-Control"] == "public, max-age=60"
    assert session_response.headers["Cache-Control"] == "private, max-age=10"
    assert user_response.headers["Cache-Control"] == "private, no-cache, must-revalidate"
    assert asset_response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert asset_response.headers["Vary"] == "Accept-Encoding, Authorization"


def test_cors_config_uses_env_or_safe_defaults(monkeypatch):
    cors_config = reload_cors_module(monkeypatch, allowed_origins="https://a.example, https://b.example")
    assert cors_config.ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]

    cors_config = reload_cors_module(monkeypatch, production_domain="teachr.live")
    assert "https://teachr.live" in cors_config.ALLOWED_ORIGINS
    assert cors_config.ALLOWED_METHODS == ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]


def test_jwt_config_validates_and_fails_closed(monkeypatch, capsys):
    jwt_config = reload_jwt_config_module(
        monkeypatch,
        secret="Asecure-secret-1234567890-abcdefghijklmnopqrstuvwxyz",
        environment="testing",
    )
    assert jwt_config.validate_jwt_secret("abc") == (
        False,
        "JWT_SECRET must be at least 32 characters long (current: 3)",
    )
    assert jwt_config.validate_jwt_secret("a" * 40) == (
        False,
        "JWT_SECRET should contain both letters and numbers for better security",
    )
    assert jwt_config.should_fail_closed_on_weak_jwt_secret() is False

    with pytest.raises(SystemExit):
        reload_jwt_config_module(monkeypatch, secret="secret", environment="production")

    warning_module = reload_jwt_config_module(monkeypatch, secret="secret", environment="development")
    assert warning_module.should_fail_closed_on_weak_jwt_secret() is False
    assert "WARNING: Running in development mode with weak JWT secret" in capsys.readouterr().out

    cloud_run_module = reload_jwt_config_module(
        monkeypatch,
        secret="Asecure-secret-1234567890-abcdefghijklmnopqrstuvwxyz",
        environment="development",
        k_service="auth",
    )
    assert cloud_run_module.is_cloud_run_runtime() is True
    assert cloud_run_module.should_fail_closed_on_weak_jwt_secret() is True

    reload_jwt_config_module(
        monkeypatch,
        secret="Asecure-secret-1234567890-abcdefghijklmnopqrstuvwxyz",
        environment="testing",
    )


def test_logging_setup_uses_structured_and_colored_formatters():
    import shared.logging_config as logging_config

    structured_logger = logging_config.setup_logger("structured-test", structured=True)
    colored_logger = logging_config.setup_logger("colored-test", level="debug")

    structured_handler = structured_logger.handlers[0]
    colored_handler = colored_logger.handlers[0]

    assert isinstance(structured_handler.formatter, logging_config.StructuredFormatter)
    assert isinstance(colored_handler.formatter, logging_config.ColoredFormatter)

    record = logging.LogRecord("structured-test", logging.INFO, __file__, 10, "hello", (), None)
    assert '"message": "hello"' in structured_handler.format(record)

    colored_record = logging.LogRecord("colored-test", logging.INFO, __file__, 10, "hello", (), None)
    assert "\u001b[" in colored_handler.format(colored_record)
