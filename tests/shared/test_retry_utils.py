import pytest

from shared import retry_utils


def test_retry_with_backoff_retries_until_success(monkeypatch):
    sleeps = []
    attempts = {"count": 0}
    retry_events = []

    monkeypatch.setattr(retry_utils.time, "sleep", lambda duration: sleeps.append(duration))

    @retry_utils.retry_with_backoff(retries=3, backoff_factor=2, exceptions=(ValueError,), on_retry=lambda attempt, error: retry_events.append((attempt, str(error))))
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("not yet")
        return "ok"

    assert flaky() == "ok"
    assert sleeps == [1, 2]
    assert retry_events == [(0, "not yet"), (1, "not yet")]


def test_retry_with_backoff_raises_after_last_attempt(monkeypatch):
    monkeypatch.setattr(retry_utils.time, "sleep", lambda duration: None)

    @retry_utils.retry_with_backoff(retries=2, exceptions=(ValueError,))
    def always_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        always_fail()


def test_safe_execute_returns_default_on_error():
    assert retry_utils.safe_execute(lambda: 1 + 1) == 2
    assert retry_utils.safe_execute(lambda: (_ for _ in ()).throw(RuntimeError("bad")), default="fallback", log_errors=False) == "fallback"


def test_retry_on_api_error_only_retries_retryable_errors(monkeypatch):
    monkeypatch.setattr(retry_utils.time, "sleep", lambda duration: None)
    attempts = {"count": 0}

    @retry_utils.retry_on_api_error(retries=2)
    def flaky():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise retry_utils.RetryableError("retry me")
        return "done"

    assert flaky() == "done"


def test_error_handler_suppresses_or_re_raises():
    with retry_utils.ErrorHandler("suppressed"):
        raise ValueError("ignored")

    with pytest.raises(ValueError, match="raised"):
        with retry_utils.ErrorHandler("raised", raise_on_error=True):
            raise ValueError("raised")
