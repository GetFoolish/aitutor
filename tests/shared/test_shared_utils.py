import asyncio
import base64
import importlib
import json
import logging
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from shared import cache_middleware
from shared import cache_utils
from shared import circuit_breaker
from shared import cors_config
from shared import db_utils
from shared import field_filter
from shared import llm_cache
from shared import logging_config
from shared import model_router
from shared import pagination
from shared import retry_utils


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.deleted = []

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def keys(self, pattern):
        prefix = pattern.removesuffix("*")
        return [key for key in self.store if key.startswith(prefix)]

    def delete(self, *keys):
        self.deleted.extend(keys)
        for key in keys:
            self.store.pop(key, None)

    def info(self, section):
        return {"keyspace_hits": 2, "keyspace_misses": 1}

    def dbsize(self):
        return len(self.store)


class FakeCursor:
    def __init__(self, items):
        self.items = items

    def sort(self, field, direction):
        reverse = direction == -1
        return FakeCursor(sorted(self.items, key=lambda item: item[field], reverse=reverse))

    def limit(self, count):
        return self.items[:count]


class FakeCollection:
    def __init__(self, items):
        self.items = items
        self.last_query = None

    def find(self, query):
        self.last_query = query
        return FakeCursor(self.items)


class DemoFilterResponse(field_filter.FilterableResponse):
    user_id: str
    email: str
    hidden: str


def test_cache_utils_caches_reads_and_invalidates(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", fake_redis)

    @cache_utils.cache_response(ttl=60, prefix="skills")
    async def fetch_value(name):
        return {"name": name}

    key = cache_utils.generate_cache_key("skills", "algebra")
    assert key.startswith("skills:")

    first = asyncio.run(fetch_value("algebra"))
    second = asyncio.run(fetch_value("algebra"))

    assert first == second == {"name": "algebra"}
    assert len(fake_redis.store) == 1

    cache_utils.invalidate_cache("skills")
    assert fake_redis.deleted
    assert cache_utils.get_cache_stats()["available"] is True


def test_circuit_breaker_handles_sync_and_async_failures():
    breaker = circuit_breaker.CircuitBreaker(failure_threshold=2, timeout=0.01, recovery_timeout=0.01)

    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
    assert breaker.get_state()["state"] == "open"

    timeout_breaker = circuit_breaker.CircuitBreaker(failure_threshold=2, timeout=0.01, recovery_timeout=0.01)

    async def sleepy():
        await asyncio.sleep(0.05)
        return "done"

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(timeout_breaker.call_async(sleepy))


def test_circuit_breaker_decorator_recovers_successfully():
    calls = {"count": 0}

    @circuit_breaker.circuit_breaker(failure_threshold=2, timeout=0.1, recovery_timeout=0.01)
    async def protected():
        calls["count"] += 1
        return "ok"

    assert asyncio.run(protected()) == "ok"
    assert calls["count"] == 1


def test_db_utils_pagination_and_query_monitor():
    params = db_utils.PaginationParams(page=0, limit=999, max_limit=50)
    assert params.to_dict() == {"page": 1, "limit": 50, "offset": 0}

    response = db_utils.paginate(items=[1, 2], total=5, page=2, limit=2)
    assert response.total_pages == 3
    assert response.has_next is True
    assert response.has_prev is True

    monitor = db_utils.QueryMonitor(slow_query_threshold=0.1)
    for _ in range(6):
        monitor.monitor_query("skills-by-grade", 0.2, params={"grade": "K"})
    assert monitor.get_slow_queries(limit=1)[0]["query_name"] == "skills-by-grade"
    assert "skills-by-grade" in monitor.get_recommendations()[0]


def test_field_filter_helpers_cover_sync_and_async_wrappers():
    payload = {"user_id": "u1", "email": "student@example.com", "nested": {"hidden": "x", "shown": "y"}}
    filtered = field_filter.filter_fields(payload, fields={"user_id", "nested"}, exclude={"hidden"})
    assert filtered == {"user_id": "u1", "nested": {}}
    assert field_filter.parse_fields_query(" user_id , email ") == {"user_id", "email"}
    assert "user_id" in field_filter.get_field_set("user_minimal")

    model = DemoFilterResponse(user_id="u1", email="student@example.com", hidden="secret")
    assert model.dict_filtered(fields={"user_id"}) == {"user_id": "u1"}

    @field_filter.filterable_response(default_exclude={"hidden"})
    def sync_endpoint(fields=None, exclude=None):
        return {"user_id": "u1", "hidden": "secret"}

    @field_filter.filterable_response()
    async def async_endpoint(fields=None, exclude=None):
        return {"user_id": "u1", "email": "student@example.com"}

    assert asyncio.run(async_endpoint(fields="user_id")) == {"user_id": "u1"}
    assert sync_endpoint() == {"user_id": "u1"}

    with pytest.raises(ValueError):
        field_filter.get_field_set("missing")


def test_pagination_helpers_cover_query_and_list_paths():
    cursor = pagination.PaginationCursor(last_id="abc", last_value=3)
    encoded = cursor.encode()
    assert pagination.PaginationCursor.decode(encoded).last_id == "abc"

    collection = FakeCollection(
        [
            {"_id": "3", "difficulty": 3},
            {"_id": "2", "difficulty": 2},
            {"_id": "1", "difficulty": 1},
        ]
    )
    result = pagination.paginate_query(collection, {}, limit=2, sort_field="difficulty", sort_descending=True)
    assert result.has_more is True
    assert result.page_size == 2
    assert result.next_cursor is not None

    page = pagination.paginate_list(["a", "b", "c"], limit=2)
    assert page.items == ["a", "b"]
    next_page = pagination.paginate_list(["a", "b", "c"], cursor=page.next_cursor, limit=2)
    assert next_page.items == ["c"]

    with pytest.raises(ValueError):
        pagination.PaginationCursor.decode("bad-cursor")


def test_retry_utils_retry_safe_execute_and_error_handler(monkeypatch):
    slept = []
    monkeypatch.setattr(retry_utils.time, "sleep", lambda seconds: slept.append(seconds))

    calls = {"count": 0}

    @retry_utils.retry_with_backoff(retries=3, backoff_factor=2, exceptions=(ValueError,))
    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("retry me")
        return "ok"

    assert flaky() == "ok"
    assert slept == [1, 2]
    assert retry_utils.safe_execute(lambda: 42) == 42
    assert retry_utils.safe_execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")), default="fallback") == "fallback"

    with retry_utils.ErrorHandler("test operation") as handler:
        raise RuntimeError("suppressed")
    assert str(handler.error) == "suppressed"

    with pytest.raises(RuntimeError):
        with retry_utils.ErrorHandler("test operation", raise_on_error=True):
            raise RuntimeError("reraised")


def test_model_router_routes_requests_and_tracks_stats():
    router = model_router.ModelRouter()

    simple = router.classify_task_complexity("greeting", context_length=10)
    complex_tier = router.classify_task_complexity("grading", context_length=9000)
    critical = router.classify_task_complexity("grading", is_final_assessment=True)

    assert simple is model_router.ComplexityTier.SIMPLE
    assert complex_tier is model_router.ComplexityTier.COMPLEX
    assert critical is model_router.ComplexityTier.CRITICAL

    config, tier = router.route_request("greeting", "Hello there")
    assert config.provider == "google"
    assert tier is model_router.ComplexityTier.SIMPLE
    assert router.estimate_cost(model_router.ModelTier.FAST, 500, 200) > 0
    assert router.get_stats()["total_calls"] == 1


def test_llm_cache_supports_eviction_hits_and_decorator(monkeypatch):
    cache = llm_cache.LRUCache(max_size=2, default_ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.size() == 2

    prompt_cache = llm_cache.PromptCache(max_size=2, default_ttl=60)
    prompt_cache.set("hello", "world", model="gpt")
    assert prompt_cache.get("hello", model="gpt") == "world"
    assert prompt_cache.get("missing", model="gpt") is None
    prompt_cache.invalidate("hello", model="gpt")
    assert prompt_cache.stats()["total_requests"] == 2

    @llm_cache.cached_llm_call(ttl=60, cache_instance=prompt_cache)
    def answer(prompt, model="gpt"):
        return prompt.upper()

    assert answer("hello", model="gpt") == "HELLO"
    assert answer("hello", model="gpt") == "HELLO"

    llm_cache.clear_cache()
    assert llm_cache.get_cache_stats()["size"] == 0


def test_logging_config_and_middlewares(monkeypatch):
    formatter = logging_config.StructuredFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {"request_id": "req-1"}
    formatted = json.loads(formatter.format(record))
    assert formatted["message"] == "hello"
    assert formatted["request_id"] == "req-1"

    logger = logging_config.setup_logger("test-logger", level="DEBUG", structured=True)
    assert logger.handlers

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    prod_logger = logging_config.get_logger("prod-logger")
    assert prod_logger.level == logging.WARNING

    app = FastAPI()
    app.add_middleware(cache_middleware.CacheControlMiddleware)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/auth/me")
    async def auth_me():
        return {"user_id": "u1"}

    with TestClient(app) as client:
        health_response = client.get("/health")
        assert health_response.headers["Cache-Control"] == "public, max-age=60"
        auth_response = client.get("/auth/me")
        assert auth_response.headers["Cache-Control"] == "private, no-cache, must-revalidate"
        assert auth_response.headers["Vary"] == "Accept-Encoding, Authorization"


def test_cors_config_uses_environment_and_defaults(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example, https://b.example")
    assert cors_config.get_allowed_origins() == ["https://a.example", "https://b.example"]

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("PRODUCTION_DOMAIN", "teachr.live")
    origins = cors_config.get_allowed_origins()
    assert "https://teachr.live" in origins
    assert "http://localhost:3000" in origins
