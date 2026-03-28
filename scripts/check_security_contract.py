#!/usr/bin/env python3

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def assert_absent(path: Path, needle: str, message: str, errors: list[str]) -> None:
    if needle in path.read_text():
        errors.append(f"{message} ({path.relative_to(PROJECT_ROOT)})")


def assert_present(path: Path, needle: str, message: str, errors: list[str]) -> None:
    if needle not in path.read_text():
        errors.append(f"{message} ({path.relative_to(PROJECT_ROOT)})")


def assert_all_present(path: Path, needles: list[str], message: str, errors: list[str]) -> None:
    content = path.read_text()
    missing = [needle for needle in needles if needle not in content]
    if missing:
        joined = ", ".join(missing)
        errors.append(f"{message}: missing {joined} ({path.relative_to(PROJECT_ROOT)})")


def assert_occurrences_at_least(path: Path, needle: str, minimum: int, message: str, errors: list[str]) -> None:
    count = path.read_text().count(needle)
    if count < minimum:
        errors.append(f"{message}: expected at least {minimum}, found {count} ({path.relative_to(PROJECT_ROOT)})")


def main() -> int:
    errors: list[str] = []

    auth_api = PROJECT_ROOT / "services" / "AuthService" / "auth_api.py"
    teaching_api = PROJECT_ROOT / "services" / "TeachingAssistant" / "api.py"
    cloudbuild = PROJECT_ROOT / "cloudbuild.yaml"
    cloudbuild_bootstrap = PROJECT_ROOT / "cloudbuild.bootstrap.yaml"

    assert_absent(
        auth_api,
        '@app.get("/auth/gemini-key")',
        "Raw Gemini key endpoint must stay disabled",
        errors,
    )
    assert_absent(
        teaching_api,
        'os.getenv("OBSERVER_API_KEY", "dev-observer-key-12345")',
        "Observer endpoints must not fall back to the default dev key",
        errors,
    )
    assert_present(
        cloudbuild,
        "--set-secrets",
        "Cloud Run deploys must use Secret Manager bindings",
        errors,
    )
    assert_present(
        cloudbuild_bootstrap,
        "--set-secrets",
        "Bootstrap deploys must use Secret Manager bindings",
        errors,
    )
    deploy_secret_contract = [
        "MONGODB_URI=${_MONGODB_URI_SECRET}",
        "OPENROUTER_API_KEY=${_OPENROUTER_API_KEY_SECRET}",
        "JWT_SECRET=${_JWT_SECRET_SECRET}",
        "GOOGLE_CLIENT_ID=${_GOOGLE_CLIENT_ID_SECRET}",
        "GOOGLE_CLIENT_SECRET=${_GOOGLE_CLIENT_SECRET_SECRET}",
        "GEMINI_API_KEY=${_GEMINI_API_KEY_SECRET}",
        "OBSERVER_API_KEY=${_OBSERVER_API_KEY_SECRET}",
        "DASH_API_URL=${_DASH_API_URL}",
    ]
    assert_all_present(
        cloudbuild,
        deploy_secret_contract,
        "Main deploy config is missing required runtime secret/env bindings",
        errors,
    )
    assert_all_present(
        cloudbuild_bootstrap,
        deploy_secret_contract,
        "Bootstrap deploy config is missing required runtime secret/env bindings",
        errors,
    )
    assert_occurrences_at_least(
        cloudbuild,
        "ENVIRONMENT=${_ENVIRONMENT}",
        4,
        "Main deploy config must set ENVIRONMENT for every backend Cloud Run service",
        errors,
    )
    assert_occurrences_at_least(
        cloudbuild_bootstrap,
        "ENVIRONMENT=${_ENVIRONMENT}",
        4,
        "Bootstrap deploy config must set ENVIRONMENT for every backend Cloud Run service",
        errors,
    )
    assert_present(
        cloudbuild,
        '_ENVIRONMENT: "REPLACE_IN_COMMAND"',
        "Main deploy config must require explicit environment substitution",
        errors,
    )
    assert_present(
        cloudbuild_bootstrap,
        '_ENVIRONMENT: "REPLACE_IN_COMMAND"',
        "Bootstrap deploy config must require explicit environment substitution",
        errors,
    )

    if errors:
        print("Security contract check failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Security contract check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
