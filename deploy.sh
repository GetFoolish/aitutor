#!/bin/bash

# Configuration
PROJECT_ID="aitutor-473420"
REGION="us-central1"

# Check environment argument
ENV=${1:-staging}  # Default to staging if no argument provided

if [ "$ENV" != "staging" ] && [ "$ENV" != "prod" ]; then
    echo "❌ Invalid environment. Use 'staging' or 'prod'"
    echo "Usage: ./deploy.sh [staging|prod]"
    exit 1
fi

echo "🚀 Deploying to Google Cloud Run - $ENV environment"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set the project
gcloud config set project $PROJECT_ID

# CORS_ORIGINS is now set explicitly in GitHub Actions workflows

# Validate required environment variables
REQUIRED_VARS=("MONGODB_URI" "MONGODB_DB_NAME" "OPENROUTER_API_KEY" "GEMINI_API_KEY" "JWT_SECRET" "GOOGLE_CLIENT_ID" "GOOGLE_CLIENT_SECRET")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please set them before running the deployment:"
    echo "   export MONGODB_URI=your_mongodb_uri"
    echo "   export MONGODB_DB_NAME=your_db_name"
    echo "   export OPENROUTER_API_KEY=your_openrouter_key"
    echo "   export GEMINI_API_KEY=your_gemini_key"
    echo "   export JWT_SECRET=your_secure_jwt_secret_key"
    echo "   export GOOGLE_CLIENT_ID=your_google_client_id"
    echo "   export GOOGLE_CLIENT_SECRET=your_google_client_secret"
    exit 1
fi

# Set optional environment variables with defaults
GEMINI_MODEL=${GEMINI_MODEL:-"models/gemini-2.5-flash-native-audio-preview-09-2025"}
MONGODB_DB_NAME=${MONGODB_DB_NAME:-"ai_tutor"}

# Set environment-specific variables
if [ "$ENV" = "staging" ]; then
    echo "📦 Deploying STAGING environment..."
    CONFIG_FILE="cloudbuild.yaml"
    SERVICE_SUFFIX="-staging"
    ENV_SUFFIX_SUB="-staging"
    
    # Try to retrieve existing service URLs, or use placeholders for first deployment
    echo "🔍 Retrieving existing service URLs (if any)..."
    
    DASH_API_URL=$(gcloud run services describe dash-api-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    SHERLOCKED_API_URL=$(gcloud run services describe sherlocked-api-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    TEACHING_ASSISTANT_API_URL=$(gcloud run services describe teaching-assistant-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    TUTOR_URL=$(gcloud run services describe tutor-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    AUTH_SERVICE_URL=$(gcloud run services describe auth-service-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    
    # Use placeholders if services don't exist yet (first deployment)
    if [ -z "$DASH_API_URL" ]; then
        echo "⚠️  DASH API not found. Using existing URL"
        DASH_API_URL="https://dash-api-staging-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$SHERLOCKED_API_URL" ]; then
        echo "⚠️  SherlockED API not found. Using existing URL"
        SHERLOCKED_API_URL="https://sherlocked-api-staging-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$TEACHING_ASSISTANT_API_URL" ]; then
        echo "⚠️  TeachingAssistant API not found. Using existing URL"
        TEACHING_ASSISTANT_API_URL="https://teaching-assistant-staging-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$TUTOR_URL" ]; then
        echo "⚠️  Tutor service not found. Using existing URL"
        TUTOR_URL="https://tutor-staging-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$AUTH_SERVICE_URL" ]; then
        echo "⚠️  Auth Service not found. Using existing URL"
        AUTH_SERVICE_URL="https://auth-service-staging-utmfhquz6a-uc.a.run.app"
    fi
else
    echo "📦 Deploying PRODUCTION environment..."
    CONFIG_FILE="cloudbuild.yaml"
    SERVICE_SUFFIX=""
    ENV_SUFFIX_SUB=""
    
    # Try to retrieve existing service URLs, or use placeholders for first deployment
    echo "🔍 Retrieving existing service URLs (if any)..."
    
    DASH_API_URL=$(gcloud run services describe dash-api --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    SHERLOCKED_API_URL=$(gcloud run services describe sherlocked-api --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    TEACHING_ASSISTANT_API_URL=$(gcloud run services describe teaching-assistant --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    TUTOR_URL=$(gcloud run services describe tutor --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    AUTH_SERVICE_URL=$(gcloud run services describe auth-service --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")

    # Use placeholders if services don't exist yet (first deployment)
    if [ -z "$DASH_API_URL" ]; then
        echo "⚠️  DASH API not found. Will be created on first deployment"
        DASH_API_URL="https://dash-api-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$SHERLOCKED_API_URL" ]; then
        echo "⚠️  SherlockED API not found. Will be created on first deployment"
        SHERLOCKED_API_URL="https://sherlocked-api-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$TEACHING_ASSISTANT_API_URL" ]; then
        echo "⚠️  TeachingAssistant API not found. Will be created on first deployment"
        TEACHING_ASSISTANT_API_URL="https://teaching-assistant-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$TUTOR_URL" ]; then
        echo "⚠️  Tutor service not found. Will be created on first deployment"
        TUTOR_URL="https://tutor-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$AUTH_SERVICE_URL" ]; then
        echo "⚠️  Auth Service not found. Will be created on first deployment"
        AUTH_SERVICE_URL="https://auth-service-utmfhquz6a-uc.a.run.app"
    fi
fi

# Convert HTTPS to WSS for WebSocket URLs
TUTOR_WS_URL=$(echo $TUTOR_URL | sed 's/https/wss/')

echo "🔗 Using URLs:"
echo "  DASH API: $DASH_API_URL"
echo "  SherlockED: $SHERLOCKED_API_URL"
echo "  TeachingAssistant: $TEACHING_ASSISTANT_API_URL"
echo "  Tutor: $TUTOR_URL"
echo "  Auth Service: $AUTH_SERVICE_URL"
echo ""

# Submit build with substitutions
# Use alternate delimiter (^@^) to handle commas in CORS_ORIGINS
# The ^@^ syntax tells gcloud to use @ as delimiter instead of comma
# Encode MONGODB_URI in base64 to prevent Cloud Build substitution conflicts
echo "📤 Submitting Cloud Build job..."
# Base64 encode the MongoDB URI to avoid special character issues
# Use Python for cross-platform base64 encoding (works on Linux, macOS, Windows)
ENCODED_MONGODB_URI=$(python3 -c "import base64, sys; print(base64.b64encode('$MONGODB_URI'.encode('utf-8')).decode('utf-8'))" 2>/dev/null || python -c "import base64, sys; print(base64.b64encode('$MONGODB_URI'.encode('utf-8')).decode('utf-8'))")
gcloud builds submit \
  --config=$CONFIG_FILE \
  --substitutions=^@^_ENV_SUFFIX="$ENV_SUFFIX_SUB"@_MONGODB_URI="$ENCODED_MONGODB_URI"@_MONGODB_DB_NAME="$MONGODB_DB_NAME"@_OPENROUTER_API_KEY="$OPENROUTER_API_KEY"@_GEMINI_API_KEY="$GEMINI_API_KEY"@_GEMINI_MODEL="$GEMINI_MODEL"@_JWT_SECRET="$JWT_SECRET"@_GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID"@_GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET"@_DASH_API_URL="$DASH_API_URL"@_SHERLOCKED_API_URL="$SHERLOCKED_API_URL"@_TEACHING_ASSISTANT_API_URL="$TEACHING_ASSISTANT_API_URL"@_TUTOR_WS="$TUTOR_WS_URL"@_AUTH_SERVICE_URL="$AUTH_SERVICE_URL"@_FRONTEND_URL="$FRONTEND_URL"@_CORS_ORIGINS="$CORS_ORIGINS" \
  .

# Get actual deployed URLs
echo ""
echo "🔍 Retrieving service URLs..."

DASH_URL=$(gcloud run services describe dash-api$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
SHERLOCKED_URL=$(gcloud run services describe sherlocked-api$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
TEACHING_ASSISTANT_URL=$(gcloud run services describe teaching-assistant$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
TUTOR_URL=$(gcloud run services describe tutor$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
AUTH_SERVICE_URL=$(gcloud run services describe auth-service$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
FRONTEND_URL=$(gcloud run services describe tutor-frontend$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)

# Convert to WSS
TUTOR_WS_URL=$(echo $TUTOR_URL | sed 's/https/wss/')

echo ""
echo "🎉 Deployment Complete! ($ENV environment)"
echo ""
echo "📝 Service URLs:"
echo "  🌐 Frontend:           $FRONTEND_URL"
echo "  🔐 Auth Service:       $AUTH_SERVICE_URL"
echo "  🔧 DASH API:           $DASH_URL"
echo "  🕵️  SherlockED:         $SHERLOCKED_URL"
echo "  👨‍🏫 TeachingAssistant:  $TEACHING_ASSISTANT_URL"
echo "  🎓 Tutor Service:      $TUTOR_URL"
echo ""
echo "🔗 WebSocket URLs:"
echo "  Tutor:              $TUTOR_WS_URL"
echo ""

if [ "$ENV" = "staging" ]; then
    echo "💡 Note: If this is your first staging deployment, update this script with the actual URLs above"
    echo "    and redeploy to use correct frontend URLs."
    echo ""
    echo "   Update these variables in deploy.sh (staging section):"
    echo "   DASH_API_URL=\"$DASH_URL\""
    echo "   SHERLOCKED_API_URL=\"$SHERLOCKED_URL\""
    echo "   TEACHING_ASSISTANT_API_URL=\"$TEACHING_ASSISTANT_URL\""
    echo "   TUTOR_URL=\"$TUTOR_URL\""
    echo "   AUTH_SERVICE_URL=\"$AUTH_SERVICE_URL\""
else
    echo "💡 Note: If this is your first production deployment, update this script with the actual URLs above"
    echo "    and redeploy to use correct frontend URLs."
    echo ""
    echo "   Update these variables in deploy.sh (production section):"
    echo "   DASH_API_URL=\"$DASH_URL\""
    echo "   SHERLOCKED_API_URL=\"$SHERLOCKED_URL\""
    echo "   TEACHING_ASSISTANT_API_URL=\"$TEACHING_ASSISTANT_URL\""
    echo "   TUTOR_URL=\"$TUTOR_URL\""
    echo "   AUTH_SERVICE_URL=\"$AUTH_SERVICE_URL\""
fi

