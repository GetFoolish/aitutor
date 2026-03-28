#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="aitutor-473420"
REGION="us-central1"
ENVIRONMENT_NAME="${1:-staging}"

if [[ "$ENVIRONMENT_NAME" != "staging" && "$ENVIRONMENT_NAME" != "prod" ]]; then
    echo "❌ Invalid environment. Use 'staging' or 'prod'."
    echo "Usage: ./deploy.sh [staging|prod]"
    exit 1
fi

if [[ "$ENVIRONMENT_NAME" == "staging" ]]; then
    ENV_SUFFIX="-staging"
    RUNTIME_ENVIRONMENT="staging"
else
    ENV_SUFFIX=""
    RUNTIME_ENVIRONMENT="production"
fi

required_vars=(
    MONGODB_DB_NAME
    MONGODB_URI_SECRET
    OPENROUTER_API_KEY_SECRET
    GEMINI_API_KEY_SECRET
    JWT_SECRET_SECRET
    GOOGLE_CLIENT_ID_SECRET
    GOOGLE_CLIENT_SECRET_SECRET
    OBSERVER_API_KEY_SECRET
    GOOGLE_CLIENT_ID_PUBLIC
    FRONTEND_URL
    ALLOWED_ORIGINS
)

for var_name in "${required_vars[@]}"; do
    if [[ -z "${!var_name:-}" ]]; then
        echo "❌ Missing required environment variable: $var_name"
        exit 1
    fi
done

GEMINI_MODEL="${GEMINI_MODEL:-models/gemini-2.5-flash-native-audio-preview-09-2025}"

describe_service_url() {
    local service_name="$1"
    gcloud run services describe "$service_name" \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --format 'value(status.url)' 2>/dev/null || true
}

collect_service_urls() {
    DASH_API_URL="$(describe_service_url "dash-api${ENV_SUFFIX}")"
    SHERLOCKED_API_URL="$(describe_service_url "sherlocked-api${ENV_SUFFIX}")"
    TEACHING_ASSISTANT_API_URL="$(describe_service_url "teaching-assistant${ENV_SUFFIX}")"
    AUTH_SERVICE_URL="$(describe_service_url "auth-service${ENV_SUFFIX}")"
}

bootstrap_backend_if_needed() {
    if [[ -n "$DASH_API_URL" && -n "$SHERLOCKED_API_URL" && -n "$TEACHING_ASSISTANT_API_URL" && -n "$AUTH_SERVICE_URL" ]]; then
        return
    fi

    echo "🔁 Bootstrapping backend services for first-time deployment..."
    gcloud builds submit \
        --project "$PROJECT_ID" \
        --config=cloudbuild.bootstrap.yaml \
        --substitutions="_ENV_SUFFIX=${ENV_SUFFIX},_MONGODB_DB_NAME=${MONGODB_DB_NAME},_MONGODB_URI_SECRET=${MONGODB_URI_SECRET},_OPENROUTER_API_KEY_SECRET=${OPENROUTER_API_KEY_SECRET},_GEMINI_API_KEY_SECRET=${GEMINI_API_KEY_SECRET},_JWT_SECRET_SECRET=${JWT_SECRET_SECRET},_GOOGLE_CLIENT_ID_SECRET=${GOOGLE_CLIENT_ID_SECRET},_GOOGLE_CLIENT_SECRET_SECRET=${GOOGLE_CLIENT_SECRET_SECRET},_OBSERVER_API_KEY_SECRET=${OBSERVER_API_KEY_SECRET},_ENVIRONMENT=${RUNTIME_ENVIRONMENT},_GEMINI_MODEL=${GEMINI_MODEL},_FRONTEND_URL=${FRONTEND_URL},_ALLOWED_ORIGINS=${ALLOWED_ORIGINS}" \
        .

    collect_service_urls
}

echo "🚀 Deploying AI Tutor to $ENVIRONMENT_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

gcloud config set project "$PROJECT_ID" >/dev/null

collect_service_urls
bootstrap_backend_if_needed

missing_urls=()
for service_name in DASH_API_URL SHERLOCKED_API_URL TEACHING_ASSISTANT_API_URL AUTH_SERVICE_URL; do
    if [[ -z "${!service_name:-}" ]]; then
        missing_urls+=("$service_name")
    fi
done

if [[ ${#missing_urls[@]} -gt 0 ]]; then
    echo "❌ Could not resolve deployed service URLs:"
    printf '   - %s\n' "${missing_urls[@]}"
    exit 1
fi

echo "🌱 Seeding compatible runtime MongoDB data when required..."
python3 scripts/seed_runtime_data.py

echo "🔍 Verifying seeded MongoDB data..."
python3 scripts/verify_seed_data.py

echo "Resolved service URLs:"
echo "  DASH API:           $DASH_API_URL"
echo "  SherlockED API:     $SHERLOCKED_API_URL"
echo "  TeachingAssistant:  $TEACHING_ASSISTANT_API_URL"
echo "  Auth Service:       $AUTH_SERVICE_URL"
echo "  Frontend:           $FRONTEND_URL"
echo ""

gcloud builds submit \
    --project "$PROJECT_ID" \
    --config=cloudbuild.yaml \
    --substitutions="_ENV_SUFFIX=${ENV_SUFFIX},_MONGODB_DB_NAME=${MONGODB_DB_NAME},_MONGODB_URI_SECRET=${MONGODB_URI_SECRET},_OPENROUTER_API_KEY_SECRET=${OPENROUTER_API_KEY_SECRET},_GEMINI_API_KEY_SECRET=${GEMINI_API_KEY_SECRET},_JWT_SECRET_SECRET=${JWT_SECRET_SECRET},_GOOGLE_CLIENT_ID_SECRET=${GOOGLE_CLIENT_ID_SECRET},_GOOGLE_CLIENT_SECRET_SECRET=${GOOGLE_CLIENT_SECRET_SECRET},_OBSERVER_API_KEY_SECRET=${OBSERVER_API_KEY_SECRET},_ENVIRONMENT=${RUNTIME_ENVIRONMENT},_GEMINI_MODEL=${GEMINI_MODEL},_DASH_API_URL=${DASH_API_URL},_SHERLOCKED_API_URL=${SHERLOCKED_API_URL},_TEACHING_ASSISTANT_API_URL=${TEACHING_ASSISTANT_API_URL},_AUTH_SERVICE_URL=${AUTH_SERVICE_URL},_FRONTEND_URL=${FRONTEND_URL},_ALLOWED_ORIGINS=${ALLOWED_ORIGINS},_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID_PUBLIC}" \
    .

FRONTEND_DEPLOY_URL="$(describe_service_url "tutor-frontend${ENV_SUFFIX}")"

echo ""
echo "✅ Deployment complete"
echo "  Frontend:           ${FRONTEND_DEPLOY_URL:-unknown}"
echo "  Auth Service:       $AUTH_SERVICE_URL"
echo "  DASH API:           $DASH_API_URL"
echo "  SherlockED API:     $SHERLOCKED_API_URL"
echo "  TeachingAssistant:  $TEACHING_ASSISTANT_API_URL"
