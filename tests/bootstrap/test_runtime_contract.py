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


def test_deploy_workflows_defer_seed_verification_until_after_first_bootstrap():
    staging_workflow = read(".github/workflows/deploy-staging.yml")
    production_workflow = read(".github/workflows/deploy-production.yml")

    assert "Detect first-time backend bootstrap" in staging_workflow
    assert "if: env.BOOTSTRAP_REQUIRED != 'true'" in staging_workflow
    assert "Skipping pre-deploy seed verification because backend bootstrap is required." in staging_workflow

    assert "Detect first-time backend bootstrap" in production_workflow
    assert "if: env.BOOTSTRAP_REQUIRED != 'true'" in production_workflow
    assert "Skipping pre-deploy seed verification because backend bootstrap is required." in production_workflow


def test_deploy_contract_sets_runtime_environment_explicitly_in_cloudbuild():
    deploy_script = read("deploy.sh")
    cloudbuild = read("cloudbuild.yaml")
    cloudbuild_bootstrap = read("cloudbuild.bootstrap.yaml")

    assert 'RUNTIME_ENVIRONMENT="staging"' in deploy_script
    assert 'RUNTIME_ENVIRONMENT="production"' in deploy_script
    assert "_ENVIRONMENT=${RUNTIME_ENVIRONMENT}" in deploy_script
    assert '_ENVIRONMENT: "REPLACE_IN_COMMAND"' in cloudbuild
    assert '_ENVIRONMENT: "REPLACE_IN_COMMAND"' in cloudbuild_bootstrap
    assert cloudbuild.count("ENVIRONMENT=${_ENVIRONMENT}") >= 4
    assert cloudbuild_bootstrap.count("ENVIRONMENT=${_ENVIRONMENT}") >= 4


def test_deploy_script_verifies_seed_data_after_bootstrap():
    deploy_script = read("deploy.sh")

    bootstrap_idx = deploy_script.index("bootstrap_backend_if_needed")
    seed_idx = deploy_script.index('python3 scripts/seed_runtime_data.py')
    verify_idx = deploy_script.index('python3 scripts/verify_seed_data.py')

    assert bootstrap_idx < seed_idx < verify_idx
    assert "MONGODB_URI" in deploy_script


def test_cloudbuild_backend_services_require_explicit_environment():
    cloudbuild = read("cloudbuild.yaml")
    cloudbuild_bootstrap = read("cloudbuild.bootstrap.yaml")

    assert '_ENVIRONMENT: "REPLACE_IN_COMMAND"' in cloudbuild
    assert '_ENVIRONMENT: "REPLACE_IN_COMMAND"' in cloudbuild_bootstrap
    assert cloudbuild.count("ENVIRONMENT=${_ENVIRONMENT}") >= 4
    assert cloudbuild_bootstrap.count("ENVIRONMENT=${_ENVIRONMENT}") >= 4


def test_deploy_workflows_fetch_runtime_mongo_uri():
    staging = read(".github/workflows/deploy-staging.yml")
    production = read(".github/workflows/deploy-production.yml")

    assert "MONGODB_URI=$(gcloud secrets versions access latest --secret=MONGODB_URI)" in staging
    assert "MONGODB_URI=$(gcloud secrets versions access latest --secret=MONGODB_URI)" in production


def test_deploy_workflows_gate_seed_verification_on_bootstrap_state():
    for workflow_path in (
        ".github/workflows/deploy-staging.yml",
        ".github/workflows/deploy-production.yml",
    ):
        workflow = read(workflow_path)

        assert "BOOTSTRAP_REQUIRED=true" in workflow
        assert "BOOTSTRAP_REQUIRED=false" in workflow
        assert "if: env.BOOTSTRAP_REQUIRED != 'true'" in workflow
        assert "python3 scripts/verify_seed_data.py" in workflow
        assert "actions/setup-python@v5" in workflow
        assert "python -m pip install -r requirements.txt -r requirements-test.txt" in workflow


def test_sherlocked_deploy_does_not_receive_unused_jwt_secret():
    cloudbuild = read("cloudbuild.yaml")
    cloudbuild_bootstrap = read("cloudbuild.bootstrap.yaml")

    assert 'id: "deploy-sherlocked-api"' in cloudbuild
    assert 'id: "deploy-sherlocked-api"' in cloudbuild_bootstrap
    assert 'MONGODB_URI=${_MONGODB_URI_SECRET},JWT_SECRET=${_JWT_SECRET_SECRET}' not in cloudbuild
    assert 'MONGODB_URI=${_MONGODB_URI_SECRET},JWT_SECRET=${_JWT_SECRET_SECRET}' not in cloudbuild_bootstrap
