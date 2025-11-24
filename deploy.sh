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

# Validate required environment variables
REQUIRED_VARS=("MONGODB_URI" "MONGODB_DB_NAME" "OPENROUTER_API_KEY" "GEMINI_API_KEY")
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
    exit 1
fi

# Set optional environment variables with defaults
GEMINI_MODEL=${GEMINI_MODEL:-"models/gemini-2.5-flash-native-audio-preview-09-2025"}
MONGODB_DB_NAME=${MONGODB_DB_NAME:-"ai_tutor"}

# Set environment-specific variables
if [ "$ENV" = "staging" ]; then
    echo "📦 Deploying STAGING environment..."
    CONFIG_FILE="cloudbuild-staging.yaml"
    SERVICE_SUFFIX="-staging"
    
    # Try to retrieve existing service URLs, or use placeholders for first deployment
    echo "🔍 Retrieving existing service URLs (if any)..."
    
    DASH_API_URL=$(gcloud run services describe dash-api-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    SHERLOCKED_API_URL=$(gcloud run services describe sherlocked-api-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    TEACHING_ASSISTANT_API_URL=$(gcloud run services describe teaching-assistant-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    MEDIAMIXER_URL=$(gcloud run services describe mediamixer-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    TUTOR_URL=$(gcloud run services describe tutor-staging --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    
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
    if [ -z "$MEDIAMIXER_URL" ]; then
        echo "⚠️  MediaMixer not found. Using existing URL"
        MEDIAMIXER_URL="https://mediamixer-staging-utmfhquz6a-uc.a.run.app"
    fi
    if [ -z "$TUTOR_URL" ]; then
        echo "⚠️  Tutor service not found. Using existing URL"
        TUTOR_URL="https://tutor-staging-utmfhquz6a-uc.a.run.app"
    fi
else
    echo "📦 Deploying PRODUCTION environment..."
    CONFIG_FILE="cloudbuild-staging.yaml"  # Use same config for now
    SERVICE_SUFFIX=""
    
    # Production URLs (update these after first deployment)
    DASH_API_URL="https://dash-api-PLACEHOLDER.us-central1.run.app"
    SHERLOCKED_API_URL="https://sherlocked-api-PLACEHOLDER.us-central1.run.app"
    TEACHING_ASSISTANT_API_URL="https://teaching-assistant-PLACEHOLDER.us-central1.run.app"
    MEDIAMIXER_URL="https://mediamixer-PLACEHOLDER.us-central1.run.app"
    TUTOR_URL="https://tutor-PLACEHOLDER.us-central1.run.app"
fi

# Convert HTTPS to WSS for WebSocket URLs
MEDIAMIXER_WS_URL=$(echo $MEDIAMIXER_URL | sed 's/https/wss/')
TUTOR_WS_URL=$(echo $TUTOR_URL | sed 's/https/wss/')

echo "🔗 Using URLs:"
echo "  DASH API: $DASH_API_URL"
echo "  SherlockED: $SHERLOCKED_API_URL"
echo "  TeachingAssistant: $TEACHING_ASSISTANT_API_URL"
echo "  MediaMixer: $MEDIAMIXER_URL"
echo "  Tutor: $TUTOR_URL"
echo ""

# Submit build with substitutions
echo "📤 Submitting Cloud Build job..."
gcloud builds submit \
  --config=$CONFIG_FILE \
  --substitutions=_MONGODB_URI="$MONGODB_URI",_MONGODB_DB_NAME="$MONGODB_DB_NAME",_OPENROUTER_API_KEY="$OPENROUTER_API_KEY",_GEMINI_API_KEY="$GEMINI_API_KEY",_GEMINI_MODEL="$GEMINI_MODEL",_DASH_API_URL="$DASH_API_URL",_SHERLOCKED_API_URL="$SHERLOCKED_API_URL",_TEACHING_ASSISTANT_API_URL="$TEACHING_ASSISTANT_API_URL",_MEDIAMIXER_COMMAND_WS="${MEDIAMIXER_WS_URL}/command",_MEDIAMIXER_VIDEO_WS="${MEDIAMIXER_WS_URL}/video",_TUTOR_WS="$TUTOR_WS_URL" \
  .

# Get actual deployed URLs
echo ""
echo "🔍 Retrieving service URLs..."

DASH_URL=$(gcloud run services describe dash-api$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
SHERLOCKED_URL=$(gcloud run services describe sherlocked-api$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
TEACHING_ASSISTANT_URL=$(gcloud run services describe teaching-assistant$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
MEDIAMIXER_URL=$(gcloud run services describe mediamixer$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
TUTOR_URL=$(gcloud run services describe tutor$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
FRONTEND_URL=$(gcloud run services describe tutor-frontend$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)

# Convert to WSS
MEDIAMIXER_WS_URL=$(echo $MEDIAMIXER_URL | sed 's/https/wss/')
TUTOR_WS_URL=$(echo $TUTOR_URL | sed 's/https/wss/')

echo ""
echo "🎉 Deployment Complete! ($ENV environment)"
echo ""
echo "📝 Service URLs:"
echo "  🌐 Frontend:           $FRONTEND_URL"
echo "  🔧 DASH API:           $DASH_URL"
echo "  🕵️  SherlockED:         $SHERLOCKED_URL"
echo "  👨‍🏫 TeachingAssistant:  $TEACHING_ASSISTANT_URL"
echo "  📹 MediaMixer:         $MEDIAMIXER_URL"
echo "  🎓 Tutor Service:      $TUTOR_URL"
echo ""
echo "🔗 WebSocket URLs:"
echo "  MediaMixer Command: ${MEDIAMIXER_WS_URL}/command"
echo "  MediaMixer Video:   ${MEDIAMIXER_WS_URL}/video"
echo "  Tutor:              $TUTOR_WS_URL"
echo ""

if [ "$ENV" = "staging" ]; then
    echo "💡 Note: If this is your first staging deployment, update this script with the actual URLs above"
    echo "    and redeploy to use correct frontend URLs."
    echo ""
    echo "   Update these variables in deploy.sh:"
    echo "   DASH_API_URL=\"$DASH_URL\""
    echo "   SHERLOCKED_API_URL=\"$SHERLOCKED_URL\""
    echo "   TEACHING_ASSISTANT_API_URL=\"$TEACHING_ASSISTANT_URL\""
    echo "   MEDIAMIXER_URL=\"$MEDIAMIXER_URL\""
    echo "   TUTOR_URL=\"$TUTOR_URL\""
fi

