import asyncio
import json
import logging

import pytest

from shared import cache_utils, circuit_breaker, db_utils, field_filter, llm_cache, model_router, pagination, retry_utils


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def keys(self, pattern):
        prefix = pattern[:-1]
        return [key for key in self.store if key.startswith(prefix)]

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    def info(self, section):
        return {"keyspace_hits": 3, "keyspace_misses": 1}

    def dbsize(self):
        return len(self.store)


def test_cache_utils_round_trip_and_stats(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", fake_redis)

    calls = {"count": 0}

    @cache_utils.cache_response(ttl=60, prefix="quiz")
    async def load_question(question_id):
        calls["count"] += 1
        return {"question_id": question_id}

    assert cache_utils.generate_cache_key("quiz", 1).startswith("quiz:")
    assert asyncio.run(load_question("q-1")) == {"question_id": "q-1"}
    assert asyncio.run(load_question("q-1")) == {"question_id": "q-1"}
    assert calls["count"] == 1

    cache_utils.invalidate_cache("quiz")
    assert fake_redis.store == {}

    stats = cache_utils.get_cache_stats()
    assert stats["available"] is True
    assert stats["total_keys"] == 0
    assert stats["hit_rate"] == pytest.approx(0.75)

    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", False)
    assert asyncio.run(load_question("q-2")) == {"question_id": "q-2"}


def test_circuit_breaker_handles_failure_recovery_and_decorator(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(circuit_breaker.time, "time", lambda: clock["now"])

    breaker = circuit_breaker.CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)

    def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        breaker.call(fail)
    with pytest.raises(ValueError):
        breaker.call(fail)

    assert breaker.get_state()["state"] == "open"

    with pytest.raises(Exception, match="Circuit breaker OPEN"):
        breaker.call(lambda: "blocked")

    clock["now"] = 106.0
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.get_state()["state"] == "closed"

    async_breaker = circuit_breaker.CircuitBreaker(failure_threshold=1, timeout=0.001)

    async def slow():
        await asyncio.sleep(0.01)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(async_breaker.call_async(slow))

    @circuit_breaker.circuit_breaker(failure_threshold=1, timeout=1.0, recovery_timeout=1.0)
    async def wrapped(value):
        return value

    assert asyncio.run(wrapped("done")) == "done"


def test_db_utils_pagination_and_query_monitor():
    params = db_utils.PaginationParams(page=0, limit=500, max_limit=100)
    assert params.to_dict() == {"page": 1, "limit": 100, "offset": 0}

    response = db_utils.paginate(items=[1, 2], total=5, page=2, limit=2)
    assert response.total_pages == 3
    assert response.has_next is True
    assert response.has_prev is True
    assert response.to_dict()["pagination"]["total"] == 5

    monitor = db_utils.QueryMonitor(slow_query_threshold=0.5)
    monitor.monitor_query("fast", 0.1)
    for _ in range(6):
        monitor.monitor_query("search_users", 0.9, {"email": "student@example.com"})

    slow_queries = monitor.get_slow_queries()
    assert len(slow_queries) == 6
    assert monitor.get_recommendations() == [
        "Consider adding index for 'search_users' (executed 6 times slowly)"
    ]


def test_field_filter_helpers_and_decorator():
    flat = {"user_id": "user-1", "name": "Student", "secret": "hidden"}
    nested = {"user_id": "user-1", "profile": {"name": "Student", "secret": "hidden"}}

    assert field_filter.filter_fields(flat, fields={"user_id", "name"}) == {
        "user_id": "user-1",
        "name": "Student",
    }
    assert field_filter.filter_fields(nested, exclude={"secret"}) == {
        "user_id": "user-1",
        "profile": {"name": "Student"},
    }
    assert field_filter.parse_fields_query("user_id, name ,,email") == {"user_id", "name", "email"}

    class UserResponse(field_filter.FilterableResponse):
        user_id: str
        name: str
        secret: str

    assert UserResponse(user_id="user-1", name="Student", secret="hidden").dict_filtered(
        fields={"user_id", "name"}
    ) == {"user_id": "user-1", "name": "Student"}

    assert field_filter.get_field_set("user_minimal") == {"user_id", "name", "current_grade"}
    with pytest.raises(ValueError, match="Unknown field preset"):
        field_filter.get_field_set("missing")

    @field_filter.filterable_response(default_exclude={"secret"})
    def sync_endpoint(fields=None, exclude=None):
        return {"user_id": "user-1", "name": "Student", "secret": "hidden"}

    @field_filter.filterable_response()
    async def async_endpoint(fields=None, exclude=None):
        return {"user_id": "user-1", "name": "Student", "secret": "hidden"}

    assert sync_endpoint(fields="user_id") == {"user_id": "user-1"}
    assert asyncio.run(async_endpoint(exclude="secret")) == {"user_id": "user-1", "name": "Student"}


def test_model_router_routes_by_complexity_and_tracks_stats():
    router = model_router.ModelRouter()

    model, complexity = router.route_request("greeting", "hello")
    assert complexity is model_router.ComplexityTier.SIMPLE
    assert model.provider == "google"

    model, complexity = router.route_request(
        "grading",
        "complex proof",
        context_length=10_000,
        requires_reasoning=True,
    )
    assert complexity is model_router.ComplexityTier.COMPLEX
    assert model.max_tokens == 1_000_000

    model, complexity = router.route_request(
        "grading",
        "final exam",
        is_final_assessment=True,
    )
    assert complexity is model_router.ComplexityTier.CRITICAL
    assert model.name == "gpt-4-turbo"

    assert router.estimate_cost(model_router.ModelTier.FAST, 500, 500) == pytest.approx(0.00015)
    stats = router.get_stats()
    assert stats["total_calls"] == 3
    assert stats["tier_distribution"]["fast"]["calls"] == 1

    global_model, global_complexity = model_router.route_llm_request("simple_hint", "x")
    assert global_complexity is model_router.ComplexityTier.SIMPLE
    assert global_model.name == "gemini-1.5-flash"
    assert model_router.get_routing_stats()["total_calls"] >= 1


class FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field, direction):
        self.items = sorted(self.items, key=lambda item: item[field], reverse=direction == -1)
        return self

    def limit(self, limit):
        return self.items[:limit]


class FakeCollection:
    def __init__(self, items):
        self.items = list(items)

    def find(self, query):
        filtered = self.items
        for key, value in query.items():
            if isinstance(value, dict):
                if "$lt" in value:
                    filtered = [item for item in filtered if item[key] < value["$lt"]]
                if "$gt" in value:
                    filtered = [item for item in filtered if item[key] > value["$gt"]]
            else:
                filtered = [item for item in filtered if item[key] == value]
        return FakeCursor(filtered)


def test_cursor_pagination_for_lists_and_queries():
    cursor = pagination.PaginationCursor(last_id="item-2", last_value=2)
    encoded = cursor.encode()
    assert pagination.PaginationCursor.decode(encoded) == cursor

    with pytest.raises(ValueError, match="Invalid cursor"):
        pagination.PaginationCursor.decode("not-base64")

    list_page = pagination.paginate_list(["a", "b", "c"], limit=2)
    assert list_page.items == ["a", "b"]
    assert list_page.has_more is True
    assert list_page.page_size == 2

    next_page = pagination.paginate_list(["a", "b", "c"], cursor=list_page.next_cursor, limit=2)
    assert next_page.items == ["c"]
    assert next_page.has_more is False

    items = [
        {"_id": "1", "score": 1},
        {"_id": "2", "score": 2},
        {"_id": "3", "score": 3},
    ]
    page = pagination.paginate_query(
        collection=FakeCollection(items),
        query={},
        limit=2,
        sort_field="score",
        sort_descending=False,
    )
    assert [item["_id"] for item in page.items] == ["1", "2"]
    assert page.has_more is True
    assert page.next_cursor is not None

    final_page = pagination.paginate_query(
        collection=FakeCollection(items),
        query={},
        cursor=page.next_cursor,
        limit=2,
        sort_field="score",
        sort_descending=False,
    )
    assert [item["_id"] for item in final_page.items] == ["3"]
    assert final_page.has_more is False

    params = pagination.PaginationParams(limit=5, sort_order="asc")
    assert params.limit == 5


def test_retry_utils_handle_retries_defaults_and_context(monkeypatch):
    waits = []
    monkeypatch.setattr(retry_utils.time, "sleep", lambda seconds: waits.append(seconds))

    retry_events = []
    attempts = {"count": 0}

    @retry_utils.retry_with_backoff(
        retries=3,
        backoff_factor=2.0,
        exceptions=(ValueError,),
        on_retry=lambda attempt, exc: retry_events.append((attempt, str(exc))),
    )
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("retry me")
        return "ok"

    assert flaky() == "ok"
    assert waits == [1.0, 2.0]
    assert retry_events == [(0, "retry me"), (1, "retry me")]

    assert retry_utils.safe_execute(lambda: 42) == 42
    assert retry_utils.safe_execute(lambda: 1 / 0, default="fallback", log_errors=False) == "fallback"

    api_attempts = {"count": 0}

    @retry_utils.retry_on_api_error(retries=2)
    def api_call():
        api_attempts["count"] += 1
        if api_attempts["count"] == 1:
            raise retry_utils.RetryableError("try again")
        return "done"

    assert api_call() == "done"
    assert callable(retry_utils.retry_on_network_error(retries=1))
    assert callable(retry_utils.retry_on_database_error(retries=1))

    with retry_utils.ErrorHandler("processing user") as handler:
        raise ValueError("suppressed")

    assert str(handler.error) == "suppressed"

    with pytest.raises(ValueError):
        with retry_utils.ErrorHandler("processing user", raise_on_error=True):
            raise ValueError("raise me")


def test_llm_cache_supports_eviction_hits_and_global_helpers(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(llm_cache.time, "time", lambda: clock["now"])

    cache = llm_cache.LRUCache(max_size=1, default_ttl=10)
    cache.set("first", "one")
    clock["now"] = 101.0
    cache.set("second", "two")

    assert cache.get("first") is None
    assert cache.get("second") == "two"

    cache.set("expiring", "soon", ttl=1)
    clock["now"] = 200.0
    assert cache.get("expiring") is None

    prompt_cache = llm_cache.PromptCache(max_size=10, default_ttl=10)
    assert prompt_cache.get("hello", model="gpt-4") is None
    prompt_cache.set("hello", "world", model="gpt-4")
    assert prompt_cache.get("hello", model="gpt-4") == "world"
    prompt_cache.invalidate("hello", model="gpt-4")
    assert prompt_cache.get("hello", model="gpt-4") is None

    calls = {"count": 0}

    @llm_cache.cached_llm_call(ttl=10, cache_instance=prompt_cache)
    def call_model(prompt, model="default"):
        calls["count"] += 1
        return f"answer:{prompt}:{model}"

    assert call_model("question", model="gpt-4") == "answer:question:gpt-4"
    assert call_model("question", model="gpt-4") == "answer:question:gpt-4"
    assert calls["count"] == 1

    monkeypatch.setattr(llm_cache, "_prompt_cache", prompt_cache)
    assert llm_cache.get_cache_stats()["total_requests"] >= 2
    llm_cache.clear_cache()
    assert prompt_cache.stats()["size"] == 0
