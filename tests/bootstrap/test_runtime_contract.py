from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text()


def test_setup_script_is_executable():
    setup_script = PROJECT_ROOT / "setup-local-env.sh"
    assert os.access(setup_script, os.X_OK)


def test_run_tutor_rejects_placeholder_credentials_and_exports_vite_overrides():
    run_tutor = read("run_tutor.sh")

    assert 'placeholder_prefixes=(' in run_tutor
    assert '"replace-with-"' in run_tutor
    assert 'VITE_DASH_API_URL="${VITE_DASH_API_URL:-$DASH_API_URL}"' in run_tutor
    assert 'VITE_AUTH_SERVICE_URL="${VITE_AUTH_SERVICE_URL:-$AUTH_SERVICE_URL}"' in run_tutor
    assert 'wait_for_service "DASH API" "$DASH_API_URL/health" \'"ready":true\'' in run_tutor
    assert 'wait_for_service "Auth Service" "$AUTH_SERVICE_URL/health"' in run_tutor


def test_compose_uses_internal_dash_url_for_teaching_assistant():
    compose = read("docker-compose.yml")

    assert 'DASH_API_URL: ${DOCKER_DASH_API_URL:-http://dash-api:8080}' in compose
