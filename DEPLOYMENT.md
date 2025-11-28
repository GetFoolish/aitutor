# AI Tutor Deployment Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Multi-Environment Setup](#multi-environment-setup)
4. [Deployment Pipeline](#deployment-pipeline)
5. [Service Configuration](#service-configuration)
6. [URL Management](#url-management)
7. [GitHub Actions Workflows](#github-actions-workflows)
8. [Cloud Build Configuration](#cloud-build-configuration)
9. [Deployment Script](#deployment-script)
10. [Service Details](#service-details)
11. [Environment Variables](#environment-variables)
12. [Deployment Process](#deployment-process)
13. [Troubleshooting](#troubleshooting)
14. [Best Practices](#best-practices)

---

## Overview

The AI Tutor platform is deployed on **Google Cloud Platform (GCP)** using **Cloud Run** for serverless containerized services. The deployment architecture supports **multi-environment deployments** (staging and production) with automatic environment detection based on Git branches.

### Key Technologies
- **GCP Cloud Run**: Serverless container platform
- **Google Container Registry (GCR)**: Docker image storage
- **Cloud Build**: CI/CD pipeline automation
- **GitHub Actions**: Source control integration
- **Docker**: Containerization

### Services Deployed
1. **DASH API** - Adaptive learning system
2. **SherlockED API** - Question rendering engine
3. **TeachingAssistant API** - Session management
4. **Tutor Service** - Gemini Live API bridge (WebSocket)
5. **Frontend** - React application (Nginx)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Repository                             │
│  ┌──────────────┐              ┌──────────────┐                │
│  │ staging      │              │ main         │                │
│  │ branch       │              │ branch       │                │
│  └──────┬───────┘              └──────┬───────┘                │
└─────────┼──────────────────────────────┼────────────────────────┘
          │                              │
          │ Push                         │ Push
          ▼                              ▼
┌─────────────────────┐      ┌─────────────────────┐
│ GitHub Actions      │      │ GitHub Actions      │
│ deploy-staging.yml  │      │ deploy-production   │
│                     │      │ .yml                │
└──────────┬──────────┘      └──────────┬──────────┘
           │                            │
           │ ./deploy.sh staging        │ ./deploy.sh prod
           │                            │
           ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    deploy.sh Script                          │
│  - Validates environment variables                           │
│  - Retrieves existing service URLs                           │
│  - Sets SERVICE_SUFFIX (-staging or "")                      │
│  - Submits Cloud Build job with substitutions                │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           │ gcloud builds submit
                           │ --config=cloudbuild.yaml
                           │ --substitutions=...
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Google Cloud Build Pipeline                     │
│                                                              │
│  Phase 1: Build Docker Images (Parallel)                    │
│  ├── dash-api${_ENV_SUFFIX}                                 │
│  ├── sherlocked-api${_ENV_SUFFIX}                           │
│  ├── teaching-assistant${_ENV_SUFFIX}                       │
│  ├── tutor${_ENV_SUFFIX}                                    │
│  └── tutor-frontend${_ENV_SUFFIX} (waits for backends)      │
│                                                              │
│  Phase 2: Push Images to GCR (Sequential)                   │
│  └── All images pushed to gcr.io/$PROJECT_ID/...            │
│                                                              │
│  Phase 3: Deploy to Cloud Run (Sequential)                  │
│  └── All services deployed to us-central1                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Google Cloud Run Services                       │
│                                                              │
│  Staging Environment:                                        │
│  ├── dash-api-staging → https://dash-api-staging-...        │
│  ├── sherlocked-api-staging → https://sherlocked-api-...    │
│  ├── teaching-assistant-staging → https://teaching-...      │
│  ├── tutor-staging → https://tutor-staging-...              │
│  └── tutor-frontend-staging → https://tutor-frontend-...    │
│                                                              │
│  Production Environment:                                     │
│  ├── dash-api → https://dash-api-...                        │
│  ├── sherlocked-api → https://sherlocked-api-...            │
│  ├── teaching-assistant → https://teaching-assistant-...    │
│  ├── tutor → https://tutor-...                              │
│  └── tutor-frontend → https://tutor-frontend-...            │
└──────────────────────────────────────────────────────────────┘
```

---

## Multi-Environment Setup

### Environment Detection

The deployment system automatically detects the environment based on the Git branch:

| Branch | Environment | Service Suffix | Example Service Name |
|--------|-------------|----------------|---------------------|
| `staging` | Staging | `-staging` | `dash-api-staging` |
| `main` | Production | `` (empty) | `dash-api` |

### Environment Isolation

- **Complete Separation**: Staging and production services are completely isolated
- **Same Configuration**: Both environments use the same deployment process
- **Different URLs**: Each environment has its own set of service URLs
- **Shared Resources**: Both environments can share the same MongoDB and API keys (or use separate ones)

---

## Deployment Pipeline

### Complete Flow

#### 1. **Source Control Trigger**
```
Developer pushes code to branch
  ↓
GitHub Actions detects push
  ↓
Workflow file determines environment
```

#### 2. **Pre-Deployment Phase** (`deploy.sh`)
```
Validate environment variables
  ↓
Set environment-specific variables
  ├── SERVICE_SUFFIX (-staging or "")
  ├── ENV_SUFFIX_SUB (for Cloud Build)
  └── CONFIG_FILE (cloudbuild.yaml)
  ↓
Retrieve existing service URLs
  ├── Try to get from Cloud Run
  └── Use placeholders if not found
  ↓
Convert HTTPS to WSS for WebSocket
```

#### 3. **Cloud Build Submission**
```
gcloud builds submit
  ├── Config: cloudbuild.yaml
  └── Substitutions:
      ├── _ENV_SUFFIX
      ├── _MONGODB_URI
      ├── _DASH_API_URL
      ├── _SHERLOCKED_API_URL
      ├── _TEACHING_ASSISTANT_API_URL
      └── _TUTOR_WS
```

#### 4. **Build Phase** (Parallel)
```
Build Docker Images:
  ├── dash-api${_ENV_SUFFIX}
  ├── sherlocked-api${_ENV_SUFFIX}
  ├── teaching-assistant${_ENV_SUFFIX}
  ├── tutor${_ENV_SUFFIX}
  └── tutor-frontend${_ENV_SUFFIX}
      └── Receives backend URLs as build args
```

#### 5. **Push Phase** (Sequential)
```
Push Images to GCR:
  └── gcr.io/$PROJECT_ID/{service-name}${_ENV_SUFFIX}
```

#### 6. **Deploy Phase** (Sequential)
```
Deploy to Cloud Run:
  ├── Service name: {service-name}${_ENV_SUFFIX}
  ├── Image: gcr.io/$PROJECT_ID/{service-name}${_ENV_SUFFIX}
  ├── Region: us-central1
  ├── Port: 8080
  └── Environment variables injected
```

#### 7. **Post-Deployment**
```
Retrieve actual service URLs
  ↓
Display deployment summary
  ↓
Provide URL update instructions
```

---

## Service Configuration

### Service Naming Convention

All services follow a consistent naming pattern:

**Staging:**
- Service Name: `{service-base-name}-staging`
- Image Name: `gcr.io/$PROJECT_ID/{service-base-name}-staging`
- Example: `dash-api-staging`

**Production:**
- Service Name: `{service-base-name}`
- Image Name: `gcr.io/$PROJECT_ID/{service-base-name}`
- Example: `dash-api`

### Service Details

#### 1. DASH API
- **Base Name**: `dash-api`
- **Port**: 8080
- **Environment Variables**:
  - `MONGODB_URI`
  - `MONGODB_DB_NAME`
  - `OPENROUTER_API_KEY`
- **Purpose**: Adaptive learning system, question selection

#### 2. SherlockED API
- **Base Name**: `sherlocked-api`
- **Port**: 8080
- **Environment Variables**:
  - `MONGODB_URI`
  - `MONGODB_DB_NAME`
- **Purpose**: Question rendering engine (Perseus widgets)

#### 3. TeachingAssistant API
- **Base Name**: `teaching-assistant`
- **Port**: 8080
- **Environment Variables**:
  - `MONGODB_URI`
  - `MONGODB_DB_NAME`
  - `OPENROUTER_API_KEY`
- **Purpose**: Session management, conversation tracking

#### 4. Tutor Service
- **Base Name**: `tutor`
- **Port**: 8080
- **Protocol**: WebSocket (HTTP upgrade)
- **Environment Variables**:
  - `GEMINI_API_KEY`
  - `GEMINI_MODEL`
- **Special Configuration**:
  - `--timeout`: 3600 seconds (1 hour)
  - `--min-instances`: 1 (always warm)
  - `--max-instances`: 10
- **Purpose**: Gemini Live API bridge, real-time AI tutoring

#### 5. Frontend
- **Base Name**: `tutor-frontend`
- **Port**: 8080
- **Server**: Nginx
- **Build Args** (baked into static files):
  - `VITE_DASH_API_URL`
  - `VITE_SHERLOCKED_API_URL`
  - `VITE_TEACHING_ASSISTANT_API_URL`
  - `VITE_TUTOR_WS`
- **Purpose**: React application UI

---

## URL Management

### URL Generation

Cloud Run automatically generates URLs based on:
- Service name
- Region
- Project ID

**Format:**
```
https://{service-name}-{hash}-{region-code}.a.run.app
```

**Example:**
```
Service: dash-api-staging
Region: us-central1
Generated URL: https://dash-api-staging-utmfhquz6a-uc.a.run.app
```

### URL Stability

- **First Deployment**: Cloud Run generates a unique URL
- **Subsequent Deployments**: URL remains the same (unless service is deleted)
- **Service Name = URL**: The service name determines the URL pattern

### URL Flow

#### Staging Deployment:
```
1. deploy.sh retrieves existing URLs:
   dash-api-staging → https://dash-api-staging-{hash}-uc.a.run.app

2. URLs passed to Cloud Build as substitutions:
   _DASH_API_URL=https://dash-api-staging-{hash}-uc.a.run.app

3. Frontend build receives URLs:
   VITE_DASH_API_URL=https://dash-api-staging-{hash}-uc.a.run.app

4. URLs baked into frontend JavaScript bundle

5. Frontend deployed with hardcoded backend URLs
```

#### Production Deployment:
```
1. deploy.sh retrieves existing URLs:
   dash-api → https://dash-api-{hash}-uc.a.run.app

2. URLs passed to Cloud Build as substitutions:
   _DASH_API_URL=https://dash-api-{hash}-uc.a.run.app

3. Frontend build receives URLs:
   VITE_DASH_API_URL=https://dash-api-{hash}-uc.a.run.app

4. URLs baked into frontend JavaScript bundle

5. Frontend deployed with hardcoded backend URLs
```

### WebSocket URL Conversion

Tutor service uses WebSocket protocol:
```
HTTPS URL: https://tutor-staging-{hash}-uc.a.run.app
WSS URL:   wss://tutor-staging-{hash}-uc.a.run.app
```

Conversion is done automatically in `deploy.sh`:
```bash
TUTOR_WS_URL=$(echo $TUTOR_URL | sed 's/https/wss/')
```

---

## GitHub Actions Workflows

### Staging Workflow (`.github/workflows/deploy-staging.yml`)

**Trigger:**
```yaml
on:
  push:
    branches:
      - staging
```

**Steps:**
1. Checkout repository
2. Authenticate to Google Cloud
3. Set up gcloud CLI
4. Grant execute permissions to deploy.sh
5. Set environment variables from GitHub Secrets
6. Execute `./deploy.sh staging`

**Environment Variables (from Secrets):**
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `OPENROUTER_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

### Production Workflow (`.github/workflows/deploy-production.yml`)

**Trigger:**
```yaml
on:
  push:
    branches:
      - main
```

**Steps:**
1. Checkout repository
2. Authenticate to Google Cloud
3. Set up gcloud CLI
4. Grant execute permissions to deploy.sh
5. Set environment variables from GitHub Secrets
6. Execute `./deploy.sh prod`

**Note:** Uses the same secrets as staging (can be configured separately if needed)

---

## Cloud Build Configuration

### File: `cloudbuild.yaml`

This is the unified Cloud Build configuration that supports both staging and production environments.

### Key Features

1. **Dynamic Service Names**: Uses `${_ENV_SUFFIX}` substitution
2. **Parallel Builds**: Backend services build in parallel
3. **Sequential Deployment**: Services deploy in order
4. **Frontend Dependency**: Frontend waits for all backend builds

### Build Steps

#### Step 1-4: Build Backend Services (Parallel)
```yaml
- build-dash-api
- build-sherlocked-api
- build-teaching-assistant
- build-tutor
```

Each step:
- Builds Docker image
- Tags with `${_ENV_SUFFIX}`
- Uses service-specific Dockerfile

#### Step 5: Build Frontend (Waits for Backends)
```yaml
- build-frontend
  waitFor: ['build-dash-api', 'build-sherlocked-api', 'build-teaching-assistant', 'build-tutor']
```

**Special Configuration:**
- Receives backend URLs as build arguments
- URLs are baked into React bundle during build
- Uses multi-stage Docker build (Node.js builder → Nginx server)

#### Step 6-10: Push Images (Sequential)
```yaml
- push-dash-api (waits for build-dash-api)
- push-sherlocked-api (waits for build-sherlocked-api)
- push-teaching-assistant (waits for build-teaching-assistant)
- push-tutor (waits for build-tutor)
- push-frontend (waits for build-frontend)
```

#### Step 11-15: Deploy to Cloud Run (Sequential)
```yaml
- deploy-dash-api
- deploy-sherlocked-api
- deploy-teaching-assistant
- deploy-tutor
- deploy-frontend
```

### Substitutions

All substitutions are passed from `deploy.sh`:

| Substitution | Description | Example (Staging) | Example (Production) |
|--------------|-------------|-------------------|---------------------|
| `_ENV_SUFFIX` | Environment suffix | `-staging` | `` (empty) |
| `_MONGODB_URI` | MongoDB connection string | `mongodb://...` | `mongodb://...` |
| `_MONGODB_DB_NAME` | Database name | `ai_tutor` | `ai_tutor` |
| `_OPENROUTER_API_KEY` | OpenRouter API key | `sk-...` | `sk-...` |
| `_GEMINI_API_KEY` | Gemini API key | `AIza...` | `AIza...` |
| `_GEMINI_MODEL` | Gemini model name | `models/gemini-...` | `models/gemini-...` |
| `_DASH_API_URL` | DASH API URL | `https://dash-api-staging-...` | `https://dash-api-...` |
| `_SHERLOCKED_API_URL` | SherlockED API URL | `https://sherlocked-api-staging-...` | `https://sherlocked-api-...` |
| `_TEACHING_ASSISTANT_API_URL` | TeachingAssistant URL | `https://teaching-assistant-staging-...` | `https://teaching-assistant-...` |
| `_TUTOR_WS` | Tutor WebSocket URL | `wss://tutor-staging-...` | `wss://tutor-...` |

### Build Options

```yaml
options:
  machineType: 'E2_HIGHCPU_8'  # High CPU for faster builds
  logging: CLOUD_LOGGING_ONLY   # Logs to Cloud Logging

timeout: 3600s  # 1 hour timeout
```

---

## Deployment Script

### File: `deploy.sh`

The deployment script orchestrates the entire deployment process.

### Script Flow

#### 1. **Configuration**
```bash
PROJECT_ID="aitutor-473420"
REGION="us-central1"
ENV=${1:-staging}  # Default to staging
```

#### 2. **Environment Validation**
```bash
if [ "$ENV" != "staging" ] && [ "$ENV" != "prod" ]; then
    echo "❌ Invalid environment"
    exit 1
fi
```

#### 3. **Environment Variable Validation**
Checks for required variables:
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `OPENROUTER_API_KEY`
- `GEMINI_API_KEY`

#### 4. **Environment-Specific Configuration**

**Staging:**
```bash
SERVICE_SUFFIX="-staging"
ENV_SUFFIX_SUB="-staging"
CONFIG_FILE="cloudbuild.yaml"
```

**Production:**
```bash
SERVICE_SUFFIX=""
ENV_SUFFIX_SUB=""
CONFIG_FILE="cloudbuild.yaml"
```

#### 5. **URL Retrieval**

**Staging:**
```bash
DASH_API_URL=$(gcloud run services describe dash-api-staging --region us-central1 --format 'value(status.url)' 2>/dev/null || echo "")
```

**Production:**
```bash
DASH_API_URL=$(gcloud run services describe dash-api --region us-central1 --format 'value(status.url)' 2>/dev/null || echo "")
```

**Fallback:**
If service doesn't exist, uses placeholder URL for first deployment.

#### 6. **WebSocket URL Conversion**
```bash
TUTOR_WS_URL=$(echo $TUTOR_URL | sed 's/https/wss/')
```

#### 7. **Cloud Build Submission**
```bash
gcloud builds submit \
  --config=$CONFIG_FILE \
  --substitutions=_ENV_SUFFIX="$ENV_SUFFIX_SUB",...
```

#### 8. **Post-Deployment URL Retrieval**
```bash
DASH_URL=$(gcloud run services describe dash-api$SERVICE_SUFFIX --region $REGION --format 'value(status.url)' 2>/dev/null)
```

#### 9. **Deployment Summary**
Displays all service URLs and provides update instructions.

---

## Service Details

### DASH API

**Technology:** Python 3.11, FastAPI

**Dockerfile:** `services/DashSystem/Dockerfile`

**Build Process:**
1. Base image: `python:3.11-slim`
2. Install system dependencies
3. Install Python dependencies from `requirements.txt`
4. Copy application code
5. Expose port 8080
6. Run: `python -m services.DashSystem.dash_api`

**Environment Variables:**
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name (default: `ai_tutor`)
- `OPENROUTER_API_KEY`: OpenRouter API key for LLM calls

**Endpoints:**
- `GET /health`: Health check
- `GET /api/questions/{skill_id}?user_id={user_id}`: Get adaptive question
- `POST /api/submit-answer/{user_id}`: Submit answer
- `GET /api/question-displayed/{user_id}`: Track question display

**CORS Configuration:**
- Allows: `http://localhost:3000`, `https://tutor-frontend-staging-...`
- Methods: All
- Headers: All

---

### SherlockED API

**Technology:** Python 3.11, FastAPI

**Dockerfile:** `services/SherlockEDApi/Dockerfile`

**Build Process:**
1. Base image: `python:3.11-slim`
2. Install system dependencies
3. Install Python dependencies
4. Copy application code
5. Expose port 8080
6. Run: `python services/SherlockEDApi/run_backend.py`

**Environment Variables:**
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name

**Endpoints:**
- `GET /health`: Health check
- `GET /api/questions/{question_id}`: Get question with Perseus rendering

**CORS Configuration:**
- Allows: `http://localhost`, `http://localhost:3000`, `https://tutor-frontend-staging-...`
- Methods: All
- Headers: All

---

### TeachingAssistant API

**Technology:** Python 3.11, FastAPI

**Dockerfile:** `services/TeachingAssistant/Dockerfile`

**Build Process:**
1. Base image: `python:3.11-slim`
2. Install system dependencies
3. Install Python dependencies
4. Copy application code
5. Expose port 8080
6. Run: `python -m services.TeachingAssistant.api`

**Environment Variables:**
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `OPENROUTER_API_KEY`: OpenRouter API key

**Endpoints:**
- `GET /health`: Health check
- `POST /session/start`: Start tutoring session
- `POST /session/end`: End tutoring session
- `GET /session/info`: Get session information
- `POST /conversation/turn`: Record conversation turn
- `POST /question/answered`: Record question answer
- `GET /inactivity/check`: Check for inactivity (returns prompt if needed)

**CORS Configuration:**
- Allows: `http://localhost:3000`, `http://localhost:5173`, `https://tutor-frontend-staging-...`
- Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
- Headers: All
- Explicit OPTIONS handler for Cloud Run compatibility

---

### Tutor Service

**Technology:** Node.js 18, WebSocket

**Dockerfile:** `services/Tutor/Dockerfile`

**Build Process:**
1. Base image: `node:18-alpine`
2. Copy `package.json` and `package-lock.json`
3. Install dependencies: `npm install`
4. Copy `server.js`
5. Copy `system_prompts/` directory
6. Verify system prompts exist
7. Expose port 8080
8. Run: `node server.js`

**Environment Variables:**
- `PORT`: Server port (default: 8080, Cloud Run sets to 8080)
- `GEMINI_API_KEY`: Google Gemini API key
- `GEMINI_MODEL`: Gemini model name (default: `models/gemini-2.5-flash-native-audio-preview-09-2025`)

**Special Configuration:**
- **Timeout**: 3600 seconds (1 hour) - for long WebSocket connections
- **Min Instances**: 1 - keeps instance warm to avoid cold starts
- **Max Instances**: 10 - scales up for multiple users

**Protocol:**
- HTTP: Health check endpoint (`GET /health`)
- WebSocket: Upgraded on any path (frontend connects to root)

**WebSocket Message Types:**
- `connect`: Initialize Gemini Live API connection
- `disconnect`: Close Gemini session
- `realtimeInput`: Send audio/video frames to Gemini
- `send`: Send text messages to Gemini
- `toolResponse`: Send tool responses

**Origin Validation:**
- Validates WebSocket origin header
- Allows: `http://localhost:3000`, `http://localhost:5173`, `https://tutor-frontend-staging-...`

---

### Frontend

**Technology:** React, Vite, TypeScript, Nginx

**Dockerfile:** `frontend/Dockerfile` (Multi-stage build)

**Build Process:**

**Stage 1: Builder (Node.js)**
1. Base image: `node:18-alpine`
2. Set build arguments as environment variables:
   - `VITE_DASH_API_URL`
   - `VITE_SHERLOCKED_API_URL`
   - `VITE_TEACHING_ASSISTANT_API_URL`
   - `VITE_TUTOR_WS`
3. Copy `package.json` and install dependencies
4. Copy source code
5. Build: `npm run build` (creates static files in `build/`)

**Stage 2: Server (Nginx)**
1. Base image: `nginx:alpine`
2. Copy built files from builder stage
3. Configure Nginx:
   - Listen on port 8080
   - Serve static files from `/usr/share/nginx/html`
   - SPA routing: `try_files $uri $uri/ /index.html`
   - Enable gzip compression

**Build-Time URL Injection:**
- URLs are passed as build arguments
- Vite replaces `import.meta.env.VITE_*` with actual URLs
- URLs are hardcoded into JavaScript bundle
- No runtime configuration needed

**Nginx Configuration:**
```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;  # SPA routing
    }
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

---

## Environment Variables

### Required Variables

These must be set before deployment (via GitHub Secrets or export):

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGODB_DB_NAME` | Database name | `ai_tutor` |
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-v1-...` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_MODEL` | Gemini model name | `models/gemini-2.5-flash-native-audio-preview-09-2025` |

### Service-Specific Environment Variables

#### DASH API
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `OPENROUTER_API_KEY`

#### SherlockED API
- `MONGODB_URI`
- `MONGODB_DB_NAME`

#### TeachingAssistant API
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `OPENROUTER_API_KEY`

#### Tutor Service
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

#### Frontend
- URLs are build-time variables (not runtime environment variables)

---

## Deployment Process

### Manual Deployment

#### Staging:
```bash
export MONGODB_URI="your_mongodb_uri"
export MONGODB_DB_NAME="ai_tutor"
export OPENROUTER_API_KEY="your_openrouter_key"
export GEMINI_API_KEY="your_gemini_key"

./deploy.sh staging
```

#### Production:
```bash
export MONGODB_URI="your_mongodb_uri"
export MONGODB_DB_NAME="ai_tutor"
export OPENROUTER_API_KEY="your_openrouter_key"
export GEMINI_API_KEY="your_gemini_key"

./deploy.sh prod
```

### Automated Deployment (GitHub Actions)

#### Staging:
1. Push code to `staging` branch
2. GitHub Actions automatically triggers
3. Workflow runs `./deploy.sh staging`
4. Services deployed with `-staging` suffix

#### Production:
1. Push code to `main` branch
2. GitHub Actions automatically triggers
3. Workflow runs `./deploy.sh prod`
4. Services deployed without suffix

### First Deployment

**Important:** On first deployment, services don't exist yet, so URL retrieval will fail.

**Solution:**
1. Deploy services (they will be created)
2. After deployment, `deploy.sh` will display actual URLs
3. Update placeholder URLs in `deploy.sh` with actual URLs
4. Redeploy to ensure frontend has correct backend URLs

**Example:**
```bash
# After first staging deployment, update deploy.sh:
DASH_API_URL="https://dash-api-staging-{actual-hash}-uc.a.run.app"
```

---

## Troubleshooting

### Issue: Service URLs Not Displayed After Deployment

**Symptom:** `deploy.sh` shows empty URLs after deployment

**Cause:** GitHub Actions service account may not have Cloud Run Viewer permissions

**Solution:**
1. Grant `roles/run.viewer` to the service account
2. Or manually check URLs in Cloud Console
3. Or update `deploy.sh` with actual URLs after first deployment

### Issue: Frontend Can't Connect to Backends

**Symptom:** CORS errors or connection failures

**Cause:** Frontend built with incorrect backend URLs

**Solution:**
1. Verify backend URLs in `deploy.sh` are correct
2. Redeploy frontend with correct URLs
3. Check CORS configuration in backend services

### Issue: WebSocket Connection Fails

**Symptom:** Tutor service WebSocket connection rejected

**Cause:** Origin not in allowed list

**Solution:**
1. Update `allowedOrigins` in `services/Tutor/server.js`
2. Add your frontend URL to the list
3. Redeploy Tutor service

### Issue: Build Fails with "ENV_SUFFIX not found"

**Symptom:** Cloud Build fails with substitution error

**Cause:** `_ENV_SUFFIX` substitution not passed

**Solution:**
1. Verify `deploy.sh` passes `_ENV_SUFFIX` in substitutions
2. Check that `ENV_SUFFIX_SUB` is set correctly

### Issue: Services Deploy to Wrong Environment

**Symptom:** Staging services deployed without `-staging` suffix

**Cause:** Wrong environment parameter passed

**Solution:**
1. Verify GitHub Actions workflow calls correct environment
2. Check `deploy.sh` receives correct parameter
3. Verify `SERVICE_SUFFIX` is set correctly

---

## Best Practices

### 1. Environment Separation

- **Never mix staging and production**: Always use correct branch
- **Separate databases**: Consider using different `MONGODB_DB_NAME` for each environment
- **Separate API keys**: Use different keys for staging and production (optional but recommended)

### 2. URL Management

- **Update URLs after first deployment**: Replace placeholders with actual URLs
- **Version control URLs**: Keep URLs in `deploy.sh` for reference
- **Document URL changes**: Note when URLs change

### 3. Deployment Safety

- **Test in staging first**: Always test changes in staging before production
- **Monitor deployments**: Check Cloud Build logs for errors
- **Verify health checks**: Ensure all services respond to `/health` endpoint

### 4. Service Configuration

- **Keep configurations consistent**: Same Dockerfiles, same ports, same structure
- **Use environment variables**: Never hardcode secrets
- **Document changes**: Update this documentation when making changes

### 5. Cloud Run Optimization

- **Tutor service**: Keep `min-instances: 1` to avoid cold starts
- **Other services**: Can scale to zero (cost optimization)
- **Timeout settings**: Adjust based on service needs

### 6. Security

- **CORS configuration**: Keep allowed origins list minimal
- **API keys**: Store in GitHub Secrets, never commit
- **Service accounts**: Use least privilege principle

---

## Service URLs Reference

### Staging Environment

After deployment, services will be available at:

```
Frontend:           https://tutor-frontend-staging-{hash}-uc.a.run.app
DASH API:           https://dash-api-staging-{hash}-uc.a.run.app
SherlockED API:     https://sherlocked-api-staging-{hash}-uc.a.run.app
TeachingAssistant:  https://teaching-assistant-staging-{hash}-uc.a.run.app
Tutor (WebSocket):  wss://tutor-staging-{hash}-uc.a.run.app
```

### Production Environment

After deployment, services will be available at:

```
Frontend:           https://tutor-frontend-{hash}-uc.a.run.app
DASH API:           https://dash-api-{hash}-uc.a.run.app
SherlockED API:     https://sherlocked-api-{hash}-uc.a.run.app
TeachingAssistant:  https://teaching-assistant-{hash}-uc.a.run.app
Tutor (WebSocket):  wss://tutor-{hash}-uc.a.run.app
```

**Note:** `{hash}` is a unique identifier generated by Cloud Run and remains stable for each service.

---

## Deployment Checklist

### Pre-Deployment
- [ ] All code changes committed and pushed
- [ ] Environment variables set (GitHub Secrets or export)
- [ ] Branch is correct (`staging` or `main`)
- [ ] No merge conflicts

### During Deployment
- [ ] Cloud Build job starts successfully
- [ ] All Docker images build without errors
- [ ] Images push to GCR successfully
- [ ] Services deploy to Cloud Run successfully
- [ ] Health checks pass

### Post-Deployment
- [ ] Service URLs retrieved and displayed
- [ ] Frontend accessible and loads correctly
- [ ] Backend APIs respond to requests
- [ ] WebSocket connection works
- [ ] CORS errors resolved
- [ ] Update `deploy.sh` with actual URLs (if first deployment)

---

## Additional Resources

### GCP Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Container Registry Documentation](https://cloud.google.com/container-registry/docs)

### Project-Specific
- Service code: `services/` directory
- Frontend code: `frontend/` directory
- Deployment scripts: `deploy.sh`, `cloudbuild.yaml`
- GitHub Actions: `.github/workflows/` directory

---

## Support

For deployment issues:
1. Check Cloud Build logs in GCP Console
2. Check Cloud Run logs for service errors
3. Verify environment variables are set correctly
4. Ensure service account has necessary permissions
5. Review this documentation for common issues

---

**Last Updated:** 2025-11-27
**Version:** 2.0 (Multi-Environment Support)

