import pytest

from shared import circuit_breaker


def test_circuit_breaker_opens_after_failures(monkeypatch):
    breaker = circuit_breaker.CircuitBreaker(failure_threshold=2, recovery_timeout=5, expected_exception=ValueError)
    now = {"value": 100}

    monkeypatch.setattr(circuit_breaker.time, "time", lambda: now["value"])

    def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        breaker.call(fail)
    with pytest.raises(ValueError):
        breaker.call(fail)

    assert breaker.get_state()["state"] == "open"

    with pytest.raises(Exception, match="Circuit breaker OPEN"):
        breaker.call(fail)

    now["value"] = 200
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.get_state()["state"] == "closed"


@pytest.mark.asyncio
async def test_circuit_breaker_async_and_decorator():
    breaker = circuit_breaker.CircuitBreaker(timeout=1, expected_exception=ValueError)

    async def succeed():
        return "ok"

    assert await breaker.call_async(succeed) == "ok"

    @circuit_breaker.circuit_breaker(failure_threshold=1, timeout=1)
    async def wrapped():
        return "decorated"

    assert await wrapped() == "decorated"
