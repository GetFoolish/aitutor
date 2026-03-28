from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text()


def test_deploy_script_seeds_and_verifies_data_after_bootstrap_resolution():
    deploy_script = read("deploy.sh")

    assert "MONGODB_URI" in deploy_script
    assert "bootstrap_backend_if_needed" in deploy_script
    assert 'echo "🌱 Seeding compatible runtime MongoDB data when required..."' in deploy_script
    assert "python3 scripts/seed_runtime_data.py" in deploy_script
    assert 'echo "🔍 Verifying seeded MongoDB data..."' in deploy_script
    assert "python3 scripts/verify_seed_data.py" in deploy_script


def test_staging_workflow_only_runs_predeploy_seed_check_when_bootstrap_not_required():
    workflow = read(".github/workflows/deploy-staging.yml")

    assert "Detect first-time backend bootstrap" in workflow
    assert 'if: env.BOOTSTRAP_REQUIRED != \'true\'' in workflow
    assert 'if: env.BOOTSTRAP_REQUIRED == \'true\'' in workflow
    assert 'echo "MONGODB_URI=$(gcloud secrets versions access latest --secret=MONGODB_URI)"' in workflow


def test_production_workflow_only_runs_predeploy_seed_check_when_bootstrap_not_required():
    workflow = read(".github/workflows/deploy-production.yml")

    assert "Detect first-time backend bootstrap" in workflow
    assert 'if: env.BOOTSTRAP_REQUIRED != \'true\'' in workflow
    assert 'if: env.BOOTSTRAP_REQUIRED == \'true\'' in workflow
    assert 'echo "MONGODB_URI=$(gcloud secrets versions access latest --secret=MONGODB_URI)"' in workflow


def test_cloudbuild_configs_require_explicit_runtime_mode_for_each_backend_service():
    main_config = read("cloudbuild.yaml")
    bootstrap_config = read("cloudbuild.bootstrap.yaml")

    assert '_ENVIRONMENT: "REPLACE_IN_COMMAND"' in main_config
    assert '_ENVIRONMENT: "REPLACE_IN_COMMAND"' in bootstrap_config
    assert main_config.count("ENVIRONMENT=${_ENVIRONMENT}") >= 4
    assert bootstrap_config.count("ENVIRONMENT=${_ENVIRONMENT}") >= 4


def test_sherlocked_deploy_uses_least_privilege_secret_bindings():
    main_config = read("cloudbuild.yaml")
    bootstrap_config = read("cloudbuild.bootstrap.yaml")

    assert 'id: "deploy-sherlocked-api"' in main_config
    assert 'id: "deploy-sherlocked-api"' in bootstrap_config
    assert 'MONGODB_URI=${_MONGODB_URI_SECRET},JWT_SECRET=${_JWT_SECRET_SECRET}' not in main_config
    assert 'MONGODB_URI=${_MONGODB_URI_SECRET},JWT_SECRET=${_JWT_SECRET_SECRET}' not in bootstrap_config
