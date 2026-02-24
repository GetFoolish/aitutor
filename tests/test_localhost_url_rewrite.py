from starlette.requests import Request

from services.DashSystem.dash_api import _rewrite_localhost_image_urls, _rewrite_localhost_url


def _fake_request(
    host: str = "192.168.1.55:8000",
    scheme: str = "http",
    forwarded_host: str | None = None,
    forwarded_proto: str | None = None,
) -> Request:
    headers = []
    if host:
        headers.append((b"host", host.encode("utf-8")))
    if forwarded_host:
        headers.append((b"x-forwarded-host", forwarded_host.encode("utf-8")))
    if forwarded_proto:
        headers.append((b"x-forwarded-proto", forwarded_proto.encode("utf-8")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": scheme,
        "path": "/",
        "query_string": b"",
        "headers": headers,
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }
    return Request(scope)


def test_rewrite_localhost_url_to_request_origin() -> None:
    rewritten = _rewrite_localhost_url(
        "http://localhost:8000/static/images/example.png?x=1",
        "https://preview.aitutor.dev",
    )
    assert rewritten == "https://preview.aitutor.dev/static/images/example.png?x=1"


def test_rewrite_skips_non_localhost_url() -> None:
    original = "https://cdn.example.com/static/images/example.png"
    rewritten = _rewrite_localhost_url(original, "https://preview.aitutor.dev")
    assert rewritten == original


def test_rewrite_image_widget_urls_in_payload() -> None:
    payload = {
        "question": {
            "widgets": {
                "image 1": {
                    "type": "image",
                    "options": {
                        "backgroundImage": {
                            "url": "http://localhost:8000/static/images/a.png",
                            "width": 400,
                            "height": 300,
                        }
                    },
                }
            }
        }
    }
    request = _fake_request(host="10.0.0.22:8010")

    _rewrite_localhost_image_urls(payload, request)

    rewritten = payload["question"]["widgets"]["image 1"]["options"]["backgroundImage"]["url"]
    assert rewritten == "http://10.0.0.22:8010/static/images/a.png"


def test_rewrite_respects_forwarded_headers() -> None:
    payload = {
        "question": {
            "widgets": {
                "image 1": {
                    "type": "image",
                    "options": {
                        "backgroundImage": {
                            "url": "http://127.0.0.1:8000/static/images/b.png",
                            "width": 400,
                            "height": 300,
                        }
                    },
                }
            }
        }
    }
    request = _fake_request(
        host="10.0.0.22:8010",
        forwarded_host="staging.aitutor.dev",
        forwarded_proto="https",
    )

    _rewrite_localhost_image_urls(payload, request)

    rewritten = payload["question"]["widgets"]["image 1"]["options"]["backgroundImage"]["url"]
    assert rewritten == "https://staging.aitutor.dev/static/images/b.png"
