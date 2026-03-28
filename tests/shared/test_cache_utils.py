import pytest

from shared import cache_utils


class FakeRedis:
    def __init__(self):
        self.storage = {}
        self.deleted = []

    def get(self, key):
        return self.storage.get(key)

    def setex(self, key, ttl, value):
        self.storage[key] = value

    def keys(self, pattern):
        prefix = pattern[:-1]
        return [key for key in self.storage if key.startswith(prefix)]

    def delete(self, *keys):
        self.deleted.extend(keys)
        for key in keys:
            self.storage.pop(key, None)

    def info(self, section):
        return {"keyspace_hits": 3, "keyspace_misses": 1}

    def dbsize(self):
        return len(self.storage)


@pytest.mark.asyncio
async def test_cache_response_uses_cache_when_available(monkeypatch):
    fake_redis = FakeRedis()
    cache_key = cache_utils.generate_cache_key("api", 1, topic="math")
    fake_redis.storage[cache_key] = '{"value": 42}'

    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", fake_redis)

    called = False

    @cache_utils.cache_response(prefix="api")
    async def fetch(value, topic=None):
        nonlocal called
        called = True
        return {"value": value}

    result = await fetch(1, topic="math")

    assert result == {"value": 42}
    assert called is False


@pytest.mark.asyncio
async def test_cache_response_writes_result_when_cache_misses(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", fake_redis)

    @cache_utils.cache_response(ttl=60, prefix="api")
    async def fetch(value):
        return {"value": value}

    result = await fetch(7)
    cache_key = cache_utils.generate_cache_key("api", 7)

    assert result == {"value": 7}
    assert fake_redis.storage[cache_key] == '{"value": 7}'


@pytest.mark.asyncio
async def test_cache_response_bypasses_cache_when_unavailable(monkeypatch):
    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", False)

    @cache_utils.cache_response(prefix="api")
    async def fetch():
        return {"value": "fresh"}

    assert await fetch() == {"value": "fresh"}


def test_invalidate_cache_and_get_cache_stats(monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.storage = {
        "api:first": '{"value": 1}',
        "api:second": '{"value": 2}',
        "other:key": '{"value": 3}',
    }

    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_utils, "redis_client", fake_redis)

    cache_utils.invalidate_cache("api")
    stats = cache_utils.get_cache_stats()

    assert sorted(fake_redis.deleted) == ["api:first", "api:second"]
    assert stats == {
        "available": True,
        "total_keys": 1,
        "hits": 3,
        "misses": 1,
        "hit_rate": 0.75,
    }


def test_get_cache_stats_reports_unavailable(monkeypatch):
    monkeypatch.setattr(cache_utils, "REDIS_AVAILABLE", False)

    assert cache_utils.get_cache_stats() == {"available": False}
