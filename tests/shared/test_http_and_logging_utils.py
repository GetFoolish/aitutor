import json
import logging
import sys

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from shared import cache_middleware, cors_config, logging_config


def test_cache_control_middleware_sets_route_specific_headers():
    app = FastAPI()
    app.add_middleware(cache_middleware.CacheControlMiddleware)

    @app.get("/health")
    async def health():
        return PlainTextResponse("ok")

    @app.get("/bundle.js")
    async def bundle():
        return PlainTextResponse("console.log('ok')")

    @app.get("/session/info")
    async def session_info():
        return PlainTextResponse("session")

    @app.get("/api/questions")
    async def questions():
        return PlainTextResponse("questions")

    @app.get("/auth/me")
    async def auth_me():
        return PlainTextResponse("me")

    @app.get("/dynamic")
    async def dynamic():
        return PlainTextResponse("dynamic")

    with TestClient(app) as client:
        assert client.get("/health").headers["Cache-Control"] == "public, max-age=60"
        assert client.get("/bundle.js").headers["Cache-Control"] == "public, max-age=31536000, immutable"
        assert client.get("/session/info").headers["Cache-Control"] == "private, max-age=10"
        assert (
            client.get("/api/questions").headers["Cache-Control"]
            == "public, max-age=300, stale-while-revalidate=60"
        )
        assert client.get("/auth/me").headers["Cache-Control"] == "private, no-cache, must-revalidate"
        assert client.get("/dynamic").headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        assert client.get("/dynamic").headers["Vary"] == "Accept-Encoding, Authorization"


def test_cors_config_supports_env_override_and_safe_defaults(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example, https://b.example ")
    assert cors_config.get_allowed_origins() == ["https://a.example", "https://b.example"]

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("PRODUCTION_DOMAIN", "teachr.live")
    origins = cors_config.get_allowed_origins()
    assert "https://teachr.live" in origins
    assert "https://www.teachr.live" in origins
    assert "http://localhost:3000" in origins


def test_logging_config_formats_structured_and_colored_output(monkeypatch):
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            "test.logger",
            logging.ERROR,
            __file__,
            42,
            "failure",
            (),
            exc_info=exc_info,
        )
        record.extra_fields = {"request_id": "req-1"}

    structured = logging_config.StructuredFormatter()
    payload = json.loads(structured.format(record))
    assert payload["level"] == "ERROR"
    assert payload["request_id"] == "req-1"
    assert "exception" in payload

    colored = logging_config.ColoredFormatter("%(levelname)s | %(message)s")
    colored_output = colored.format(logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None))
    assert "\u001b[" in colored_output

    logger = logging_config.setup_logger("demo.logger", level="debug", structured=True)
    assert logger.level == logging.DEBUG
    assert logger.propagate is False

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    production_logger = logging_config.get_logger("prod.logger")
    assert production_logger.level == logging.WARNING
    assert isinstance(production_logger.handlers[0].formatter, logging_config.StructuredFormatter)
