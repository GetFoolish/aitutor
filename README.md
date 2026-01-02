# AI Tutor Platform

A comprehensive adaptive learning platform that provides personalized math tutoring using AI-powered question selection, real-time voice interaction, and intelligent progress tracking. The system uses Khan Academy's Perseus question format and implements the DASH (Dynamic Adaptive System for Human learning) algorithm for adaptive difficulty adjustment.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Services](#services)
- [Frontend](#frontend)
- [Database](#database)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Development](#development)

---

## Overview

The AI Tutor Platform is a full-stack educational technology system that combines:

- **Adaptive Learning**: DASH algorithm for personalized question selection based on student performance
- **Real-time AI Tutoring**: Google Gemini Live API integration for voice-based tutoring
- **Interactive Questions**: Khan Academy Perseus widget rendering for rich math interactions
- **Progress Tracking**: Comprehensive skill-based progress monitoring and analytics
- **Question Bank Management**: Automated scraping and generation of educational content

The platform is designed for K-12 math education, with support for grades Kindergarten through 12th grade, covering topics from basic counting to advanced calculus.

---

## Features

### Core Features

1. **Adaptive Question Selection (DASH System)**
   - Memory-based learning model using forgetting curves
   - Prerequisite skill tracking
   - Adaptive difficulty adjustment
   - Grade-appropriate content filtering
   - Real-time skill progression tracking

2. **Interactive Question Display**
   - Perseus widget rendering (Khan Academy format)
   - Support for multiple question types:
     - Multiple choice
     - Numeric input
     - Graphing exercises
     - Expression input
     - Drag-and-drop matching
     - And more...

3. **Real-time AI Tutoring**
   - WebSocket-based connection to Google Gemini Live API
   - Voice and video input processing
   - Context-aware tutoring responses
   - Session management and tracking

4. **User Authentication**
   - Google OAuth integration
   - JWT-based session management
   - User profile management
   - Age-based grade calculation

5. **Progress Tracking**
   - Skill-level memory strength tracking
   - Practice count and accuracy metrics
   - Last practice time tracking
   - Visual progress indicators

6. **Teaching Assistant**
   - Session greeting and farewell messages
   - Inactivity detection and prompts
   - Question answer tracking
   - Conversation turn tracking
   - Real-time feed webhook (media, audio, transcript)
   - Dynamic instruction injection to tutor based on feed analysis

7. **Question Bank Management**
   - Automated Khan Academy question scraping
   - Skill hierarchy generation from scraped data
   - Grade level classification
   - Question ID generation and organization

### Advanced Features

- **Real-time Feed Integration**: Continuous feed of media mixer, audio input, and transcripts to Teaching Assistant via webhooks
- **Instruction Injection**: Dynamic prompt injection to tutor based on feed analysis for context-aware responses
- **Multi-environment Deployment**: Staging and production environments
- **MongoDB Integration**: Centralized data storage
- **CORS Support**: Cross-origin resource sharing for frontend-backend communication
- **Logging System**: Comprehensive logging across all services
- **Health Checks**: Service health monitoring endpoints
- **Responsive UI**: Modern React-based interface with dark mode support

---

## Architecture

The platform follows a microservices architecture with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  - Question Display                                         │
│  - Progress Tracking                                        │
│  - Real-time AI Chat (Direct Gemini Connection)            │
│  - Authentication UI                                        │
│  - Tutor Service (Frontend)                                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├──────────────────────────────────────────────┐
               │                                              │
┌──────────────▼──────────────┐    ┌─────────────────────────▼──┐
│      DASH API (FastAPI)      │    │   Teaching Assistant API  │
│  - Adaptive question selection│    │  - Session management     │
│  - Answer submission         │    │  - Inactivity detection   │
│  - Skill score tracking      │    │  - Conversation tracking   │
└──────────────┬───────────────┘    └───────────────────────────┘
               │
               ├──────────────────────────────────────────────┐
               │                                              │
┌──────────────▼──────────────┐    ┌─────────────────────────▼──┐
│   SherlockED API (FastAPI)   │    │   Auth Service (FastAPI)   │
│  - Perseus question loading  │    │  - Google OAuth            │
│  - Widget rendering          │    │  - JWT token generation    │
└──────────────┬───────────────┘    │  - User profile management │
               │                    │  - Gemini API key endpoint │
               │                    └───────────────────────────┘
               │
               ├──────────────────────────────────────────────┐
               │                                              │
┌──────────────▼──────────────┐    ┌─────────────────────────▼──┐
│      MongoDB Database        │    │   Gemini Live API (Google)  │
│  - Users                     │    │  - Real-time AI tutoring    │
│  - Skills (generated_skills) │    │  - Voice interaction        │
│  - Questions (scraped_questions)│  │  - Multimodal input        │
└──────────────────────────────┘    └───────────────────────────┘
```

### Data Flow

1. **User Authentication**: User logs in via Google OAuth → Auth Service generates JWT → Frontend stores token
2. **Question Request**: Frontend requests questions → DASH API selects adaptive questions → Loads Perseus data from MongoDB
3. **Answer Submission**: User submits answer → DASH API updates skill states → Returns updated progress
4. **AI Tutoring**: Frontend connects directly to Gemini Live API via WebSocket → Real-time voice interaction (no backend proxy)
5. **Feed Webhook**: Frontend continuously sends media mixer frames, audio input, and transcripts → Teaching Assistant webhook endpoint
6. **Instruction Injection**: Frontend requests instructions from Teaching Assistant → Receives context-aware prompts → Injects into tutor conversation
7. **Progress Tracking**: Frontend fetches skill scores → DASH API calculates memory strength → Displays progress

---

## Technology Stack

### Backend

- **Python 3.11**: Main backend language
- **FastAPI**: Web framework for REST APIs
- **MongoDB**: Primary database (via PyMongo)
- **JWT**: Authentication tokens (PyJWT)
- **Google Gemini Live API**: Real-time AI tutoring (accessed directly from frontend)
- **OpenRouter**: LLM API for question generation and teaching assistant

### Frontend

- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Perseus**: Khan Academy's question rendering library
- **React Query**: Data fetching and caching
- **Zustand**: State management
- **Radix UI**: Accessible component primitives

### Infrastructure

- **Docker**: Containerization
- **Google Cloud Run**: Serverless container hosting
- **Google Cloud Build**: CI/CD pipeline
- **Nginx**: Frontend web server
- **GitHub Actions**: Automated deployments

### Development Tools

- **mitmproxy**: Network traffic interception for question scraping
- **Selenium**: Browser automation (for scraping)
- **pytest**: Python testing (where applicable)

---

## Project Structure

```
aitutor/
├── frontend/                    # React frontend application
├── scripts/                      # Utility and maintenance scripts
│   ├── migrations/                # Migration and data synchronization
│   │   └── sync_legacy_ids.py     # Clones real questions to legacy IDs
│   ├── debug/                     # Temporary debug and verification tools
│   ├── tests/                     # Performance and rendering tests
│   └── utils/                     # General internal utilities
│
├── services/                    # Backend microservices
│   ├── DashSystem/             # DASH adaptive learning system
│   │   ├── dash_api.py         # FastAPI endpoints
│   │   ├── dash_system.py      # Core DASH algorithm
│   │   └── Dockerfile
│   │
│   ├── AuthService/             # Authentication service
│   │   ├── auth_api.py         # OAuth and JWT endpoints
│   │   ├── oauth_handler.py    # Google OAuth logic
│   │   ├── jwt_utils.py        # JWT token utilities
│   │   └── Dockerfile
│   │
│   ├── TeachingAssistant/       # Session management
│   │   ├── api.py              # Session API endpoints
│   │   ├── teaching_assistant.py # Core logic
│   │   ├── greeting_handler.py  # Greeting messages
│   │   ├── inactivity_handler.py # Inactivity detection
│   │   └── Dockerfile
│   │
│   ├── SherlockEDApi/           # Question rendering service
│   │   ├── app/
│   │   │   ├── main.py         # FastAPI app
│   │   │   ├── routes.py       # API routes
│   │   │   ├── perseus_parser.py # Perseus parsing
│   │   │   └── widget_renderer.py # Widget rendering
│   │   └── Dockerfile
│   │
│   ├── Tutor/                   # Legacy backend Tutor service (kept for reference)
│   │   ├── server.js           # WebSocket server (not used - Tutor is now in frontend)
│   │   ├── system_prompts/     # AI tutor prompts
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── QuestionBankGenerator/   # Question generation (optional)
│       ├── QuestionGeneratorAgent/
│       └── LLMBase/
│
├── managers/                     # Shared backend managers
│   ├── mongodb_manager.py      # MongoDB connection singleton
│   ├── user_manager.py         # User profile management
│   └── config_manager.py       # Configuration management
│
├── shared/                       # Shared utilities
│   ├── auth_middleware.py      # JWT authentication middleware
│   └── jwt_config.py           # JWT configuration
│
├── questionbankscrapper/        # Question scraping tools
│   ├── capture_questions.py    # Main scraping script
│   ├── generate_skills_from_scraped.py # Skill generation
│   ├── requirements.txt
│   └── README.md
│
├── logs/                         # Application logs
│   ├── dash_api.log
│   ├── auth_service.log
│   ├── teaching_assistant.log
│   └── ...
│
├── config.json                   # LLM configuration
├── requirements.txt             # Python dependencies
├── deploy.sh                    # Deployment script
├── cloudbuild.yaml              # Cloud Build configuration
├── DEPLOYMENT.md                # Deployment documentation
└── README.md                    # This file
```

---

## Services

### 1. DASH API (`services/DashSystem/`)

**Purpose**: Adaptive learning system that selects questions based on student performance.

**Key Features**:
- Memory-based learning model (forgetting curves)
- Prerequisite skill tracking
- Adaptive difficulty adjustment
- Grade-appropriate content filtering

**Endpoints**:
- `GET /api/questions/{sample_size}` - Get adaptive questions for user
- `POST /api/submit-answer` - Submit answer and update skill states
- `POST /api/question-displayed` - Track when question is displayed
- `GET /api/skill-scores` - Get all skill scores for current user
- `GET /next-question` - Get next recommended question (legacy)

**Port**: 8000 (local), 8080 (Cloud Run)

**Dependencies**: MongoDB (`generated_skills`, `scraped_questions`, `users` collections)

### 2. Auth Service (`services/AuthService/`)

**Purpose**: User authentication and profile management.

**Key Features**:
- Google OAuth integration
- JWT token generation and validation
- User profile creation and management
- Age-based grade calculation

**Endpoints**:
- `GET /auth/google` - Initiate Google OAuth flow
- `GET /auth/callback` - Handle OAuth callback
- `POST /auth/complete-setup` - Complete user setup (age, user type)
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout endpoint
- `GET /health` - Health check

**Port**: 8003 (local), 8080 (Cloud Run)

**Dependencies**: MongoDB (`users` collection)

### 3. Teaching Assistant API (`services/TeachingAssistant/`)

**Purpose**: Session management and conversation tracking.

**Key Features**:
- Session start/end tracking
- Greeting and farewell message generation
- Inactivity detection
- Question answer tracking
- Conversation turn tracking
- Real-time feed webhook for media, audio, and transcript data
- Dynamic instruction generation and injection to tutor

**Endpoints**:
- `POST /session/start` - Start tutoring session
- `POST /session/end` - End tutoring session
- `GET /session/info` - Get session information
- `POST /question/answered` - Record question answer
- `POST /conversation/turn` - Record conversation turn
- `GET /inactivity/check` - Check for inactivity (returns prompt if needed)
- `POST /webhook/feed` - Receive feed data (media, audio, transcript) from frontend
- `POST /send_instruction_to_tutor` - Get instruction prompt for tutor injection
- `GET /health` - Health check

**Port**: 8002 (local), 8080 (Cloud Run)

**Dependencies**: OpenRouter API (for LLM calls)

### 4. SherlockED API (`services/SherlockEDApi/`)

**Purpose**: Question rendering and Perseus widget support.

**Key Features**:
- Load Perseus questions from MongoDB
- Parse Perseus JSON format
- Render interactive widgets

**Endpoints**:
- `GET /api/questions/{sample_size}` - Get questions (legacy endpoint)
- `GET /health` - Health check

**Port**: 8001 (local), 8080 (Cloud Run)

**Dependencies**: MongoDB (`scraped_questions` collection)

### 5. Tutor Service (`frontend/src/services/tutor/`)

**Purpose**: Direct integration with Google Gemini Live API from frontend for real-time AI tutoring.

**Key Features**:
- Direct WebSocket connection to Gemini Live API (no backend proxy)
- System prompt management
- Audio/video frame processing
- JWT-authenticated API key retrieval from AuthService
- Error handling and reconnection logic

**Location**: Frontend service component (separate from UI components)

**Protocol**: Direct WebSocket to Gemini Live API

**Dependencies**: 
- Google Gemini API (via `@google/genai` SDK)
- AuthService for secure API key retrieval

**Architecture**:
- Frontend → Direct WebSocket → Gemini Live API
- API key fetched securely from AuthService `/auth/gemini-key` endpoint
- System prompt loaded from `frontend/public/ai_tutor_system_prompt.md`

---

## Frontend

The frontend is a React application built with TypeScript, Vite, and Tailwind CSS.

### Key Components

1. **QuestionDisplay** (`components/question-display/`)
   - Renders Perseus questions
   - Handles question navigation
   - Tracks skill changes

2. **GradingSidebar** (`components/grading-sidebar/`)
   - Displays skill progress
   - Shows memory strength, practice count, accuracy
   - Auto-scrolls to current skill

3. **SidePanel** (`components/side-panel/`)
   - Settings and controls
   - Media mixer controls
   - Scratchpad toggle

4. **AuthGuard** (`components/auth/`)
   - Protects routes requiring authentication
   - Handles JWT token validation
   - Redirects to login if needed

5. **Header** (`components/header/`)
   - Navigation bar
   - Sidebar toggles
   - User profile display

### Environment Variables

Frontend uses build-time environment variables (injected during Docker build):

- `VITE_DASH_API_URL` - DASH API endpoint
- `VITE_SHERLOCKED_API_URL` - SherlockED API endpoint
- `VITE_TEACHING_ASSISTANT_API_URL` - Teaching Assistant API endpoint
- `VITE_AUTH_SERVICE_URL` - Auth Service endpoint (for API key retrieval)

**Note**: Tutor service connects directly to Gemini Live API. API key is fetched securely from AuthService at runtime (not baked into frontend).

For local development, these default to localhost URLs.

### Key Libraries

- **@khanacademy/perseus**: Question rendering
- **@tanstack/react-query**: Data fetching and caching
- **zustand**: State management
- **@radix-ui**: Accessible UI components
- **lucide-react**: Icons

---

## Database

The platform uses **MongoDB** as the primary database with the following collections:

### Collections

1. **`users`**
   - User profiles
   - Authentication data (Google OAuth)
   - Age, grade level
   - Skill states
   - Question history

2. **`generated_skills`**
   - Skill definitions generated from scraped questions
   - Fields: `skill_id`, `name`, `grade_level`, `prerequisites`, `forgetting_rate`, `difficulty`, `order`
   - Used by DASH system for adaptive learning

3. **`scraped_questions`**
   - Questions scraped from Khan Academy
   - Fields: `questionId`, `exerciseDirName`, `assessmentData` (contains Perseus JSON)
   - Used for question rendering

4. **`perseus_questions`** (legacy)
   - Legacy collection for Perseus questions
   - May be deprecated in favor of `scraped_questions`

5. **`dash_questions`** (legacy)
   - Legacy collection for DASH questions
   - May be deprecated in favor of `scraped_questions` + `generated_skills`

### MongoDB Connection

Connection is managed by `MongoDBManager` singleton (`managers/mongodb_manager.py`):

- Connection string from `MONGODB_URI` environment variable
- Database name from `MONGODB_DB_NAME` (default: `ai_tutor`)
- Automatic connection pooling
- Health check support

---

## Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **MongoDB** (Atlas or local instance)
- **Google Cloud Account** (for Gemini API)
- **OpenRouter Account** (for LLM API access)
- **Google OAuth Credentials** (for authentication)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd aitutor
```

### Step 2: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
MONGODB_DB_NAME=ai_tutor

# OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Gemini Model
GEMINI_MODEL=models/gemini-2.5-flash-native-audio-preview-09-2025

# JWT Secret (for local development)
JWT_SECRET=your_jwt_secret_here
```

Or use the setup script:

```bash
./setup-local-env.sh
# Then edit .env with your actual values
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### Step 5: Set Up MongoDB Collections

The collections will be created automatically when the services start. However, you need to:

1. **Populate `scraped_questions`**: Use the question scraper (see `questionbankscrapper/README.md`)
2. **Setup Legacy IDs**: Run the legacy ID synchronization script to support old recruiter IDs:
   ```bash
   python scripts/migrations/sync_legacy_ids.py
   ```
3. **Generate `generated_skills`**: Run the skill generation script:

```bash
cd questionbankscrapper
python generate_skills_from_scraped.py
```

This will:
- Read questions from `scraped_questions` collection
- Generate skill hierarchy
- Calculate forgetting rates and difficulties
- Store skills in `generated_skills` collection

---

## Configuration

### Backend Configuration

#### `config.json`

LLM model configuration for question generation and teaching assistant:

```json
{
  "llm_models": {
    "question_generator": {
      "provider": "openrouter",
      "model": "anthropic/claude-3-haiku",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    "question_validator": {
      "provider": "openrouter",
      "model": "openai/gpt-4-turbo-preview",
      "temperature": 0.3,
      "max_tokens": 500
    },
    "vision_analyzer": {
      "provider": "openrouter",
      "model": "google/gemini-2.5-flash-preview-05-20:thinking",
      "temperature": 0.1,
      "max_tokens": 1000
    }
  },
  "api_endpoints": {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions"
  }
}
```

### Frontend Configuration

Frontend configuration is done via environment variables during build (see [Deployment](#deployment)).

### Service Ports (Local Development)

- **DASH API**: `http://localhost:8000`
- **SherlockED API**: `http://localhost:8001`
- **Teaching Assistant API**: `http://localhost:8002`
- **Auth Service**: `http://localhost:8003`
- **Frontend**: `http://localhost:3000` (or Vite default port)

**Note**: Tutor service is integrated in the frontend and connects directly to Gemini Live API (no separate backend service).

---

## Running Locally

### Option 1: Run All Services with Script

```bash
./run_tutor.sh
```

This script starts all backend services in the background.

### Option 2: Run Services Individually

#### Start DASH API

```bash
cd services/DashSystem
python -m services.DashSystem.dash_api
# Or: uvicorn services.DashSystem.dash_api:app --port 8000
```

#### Start Auth Service

```bash
cd services/AuthService
python -m services.AuthService.auth_api
# Or: uvicorn services.AuthService.auth_api:app --port 8003
```

#### Start Teaching Assistant API

```bash
cd services/TeachingAssistant
python -m services.TeachingAssistant.api
# Or: uvicorn services.TeachingAssistant.api:app --port 8002
```

#### Start SherlockED API

```bash
cd services/SherlockEDApi
python services/SherlockEDApi/run_backend.py
# Or: uvicorn services.SherlockEDApi.app.main:app --port 8001
```

#### Start Frontend

**Note**: Tutor service is integrated in the frontend and connects directly to Gemini Live API. No separate backend service is needed.

```bash
cd frontend
npm run dev
```

Frontend will be available at `http://localhost:3000` (or the port Vite assigns).

### Verify Services

Check health endpoints:

- DASH API: `http://localhost:8000/health` (if available)
- Auth Service: `http://localhost:8003/health`
- Teaching Assistant: `http://localhost:8002/health`
- SherlockED API: `http://localhost:8001/health`

---

## API Documentation

### DASH API

#### Get Adaptive Questions

```http
GET /api/questions/{sample_size}
Authorization: Bearer <jwt_token>
```

Returns a list of Perseus questions selected by DASH algorithm.

**Response**:
```json
[
  {
    "question": { ... },
    "answerArea": { ... },
    "hints": [ ... ],
    "dash_metadata": {
      "dash_question_id": "41.1.1.1.1_x...",
      "skill_ids": ["41.1.1.1_Count_with_small_numbers"],
      "difficulty": 0.0,
      "expected_time_seconds": 60.0,
      "slug": "41.1.1.1.1",
      "skill_names": ["Count with small numbers"]
    }
  }
]
```

#### Submit Answer

```http
POST /api/submit-answer
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "question_id": "41.1.1.1.1_x...",
  "skill_ids": ["41.1.1.1_Count_with_small_numbers"],
  "is_correct": true,
  "response_time_seconds": 29.0
}
```

**Response**:
```json
{
  "success": true,
  "affected_skills": ["41.1.1.1_Count_with_small_numbers"],
  "message": "Answer recorded successfully"
}
```

#### Get Skill Scores

```http
GET /api/skill-scores
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "skill_states": {
    "41.1.1.1_Count_with_small_numbers": {
      "name": "Count with small numbers",
      "memory_strength": 1.233,
      "last_practice_time": 1703123456.789,
      "practice_count": 10,
      "correct_count": 9
    }
  }
}
```

### Auth Service

#### Initiate Google OAuth

```http
GET /auth/google
```

**Response**:
```json
{
  "authorization_url": "https://accounts.google.com/...",
  "state": "..."
}
```

#### Complete User Setup

```http
POST /auth/complete-setup
Content-Type: application/json

{
  "setup_token": "...",
  "user_type": "student",
  "age": 5
}
```

**Response**:
```json
{
  "token": "eyJ...",
  "user": {
    "user_id": "user_...",
    "email": "user@example.com",
    "name": "User Name",
    "age": 5,
    "current_grade": "K",
    "user_type": "student"
  },
  "is_new_user": true
}
```

### Teaching Assistant API

#### Start Session

```http
POST /session/start
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "prompt": "Welcome! Let's start learning...",
  "session_info": {
    "session_active": true,
    "user_id": "user_...",
    "duration_minutes": 0.0,
    "total_questions": 0
  }
}
```

#### Check Inactivity

```http
GET /inactivity/check
Authorization: Bearer <jwt_token>
```

**Response** (if inactive):
```json
{
  "prompt": "Are you still there? Let's continue...",
  "session_info": { ... }
}
```

**Response** (if active):
```json
{
  "prompt": "",
  "session_info": { ... }
}
```

#### Receive Feed Webhook

```http
POST /webhook/feed
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "type": "media" | "audio" | "transcript" | "combined",
  "timestamp": "2025-01-27T12:00:00.000Z",
  "data": {
    "media": "base64_encoded_image",  // Optional: Media mixer frame
    "audio": "base64_encoded_audio",   // Optional: Audio input
    "transcript": "User said something" // Optional: Gemini transcript
  }
}
```

**Response**:
```json
{
  "status": "received",
  "type": "media"
}
```

#### Get Instruction for Tutor

```http
POST /send_instruction_to_tutor
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "prompt": "Instruction text to inject into tutor conversation",
  "session_info": {
    "session_active": true,
    "user_id": "user_...",
    "duration_minutes": 15.5,
    "total_questions": 3
  }
}
```

**Note**: The frontend calls this endpoint after receiving a transcript and injects the returned prompt into the tutor conversation if provided.

---

## Deployment

The platform is designed for deployment on **Google Cloud Run** with automated CI/CD via **GitHub Actions**.

### Deployment Architecture

- **Staging Environment**: Deploys from `staging` branch
- **Production Environment**: Deploys from `main` branch
- **Services**: All services containerized with Docker
- **Frontend**: Static files served via Nginx

### Deployment Process

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment documentation.

#### Quick Deployment

1. **Set up GitHub Secrets**:
   - `MONGODB_URI`
   - `MONGODB_DB_NAME`
   - `OPENROUTER_API_KEY`
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL` (optional)

2. **Push to branch**:
   - `staging` branch → deploys to staging
   - `main` branch → deploys to production

3. **GitHub Actions** automatically:
   - Builds Docker images
   - Pushes to Google Container Registry
   - Deploys to Cloud Run
   - Updates service URLs

### Manual Deployment

```bash
# Set environment variables
export MONGODB_URI="..."
export MONGODB_DB_NAME="ai_tutor"
export OPENROUTER_API_KEY="..."
export GEMINI_API_KEY="..."

# Deploy staging
./deploy.sh staging

# Deploy production
./deploy.sh prod
```

---

## Development

### Code Structure

- **Backend**: Python services in `services/`
- **Frontend**: React/TypeScript in `frontend/`
- **Shared**: Common utilities in `managers/` and `shared/`
- **Tools**: Scraping and generation tools in `questionbankscrapper/`

### Adding a New Service

1. Create service directory in `services/`
2. Add `Dockerfile`
3. Add service to `cloudbuild.yaml`
4. Update `deploy.sh` with service URL retrieval
5. Update frontend environment variables if needed

### Testing

- **Backend**: Use FastAPI's automatic OpenAPI docs at `/docs`
- **Frontend**: Run `npm run dev` for hot reload
- **Logs**: Check `logs/` directory for service logs

### Logging

All services use structured logging:

```
INFO|message|file:filename.py:line No.123
```

Log files are stored in `logs/` directory:
- `dash_api.log`
- `auth_service.log`
- `teaching_assistant.log`
- `frontend.log`

**Note**: Tutor service logs are now in browser console (frontend-based service).

### Database Migrations

MongoDB collections are created automatically. For data migrations, see `services/tools/`:
- `migrate_skills_to_mongodb.py`
- `migrate_perseus_to_mongodb.py`
- `migrate_dash_questions_to_mongodb.py`

---

## Question Bank Management

### Scraping Questions

See `questionbankscrapper/README.md` for detailed instructions on scraping Khan Academy questions.

**Quick Start**:
```bash
cd questionbankscrapper
pip install -r requirements.txt
python capture_questions.py
```

### Generating Skills

After scraping questions, generate skills:

```bash
cd questionbankscrapper
python generate_skills_from_scraped.py
```

This script:
1. Reads from `scraped_questions` collection
2. Builds skill hierarchy (Subject → Course → Unit → Lesson → Exercise)
3. Calculates grade levels
4. Calculates forgetting rates and difficulties
5. Stores in `generated_skills` collection

**Options**:
```bash
# Filter by subjects
python generate_skills_from_scraped.py --subjects math science

# All subjects (default)
python generate_skills_from_scraped.py
```

---

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check `MONGODB_URI` in `.env`
   - Verify MongoDB network access (firewall, IP whitelist)
   - Test connection: `python -c "from managers.mongodb_manager import mongo_db; mongo_db.test_connection()"`

2. **Frontend Can't Connect to Backend**
   - Check CORS configuration in backend services
   - Verify backend URLs in frontend environment variables
   - Check browser console for CORS errors

3. **Tutor Connection Fails**
   - Verify Gemini API key is accessible via AuthService `/auth/gemini-key` endpoint
   - Check browser console for connection errors
   - Verify system prompt file exists at `frontend/public/ai_tutor_system_prompt.md`
   - Check network connectivity to Gemini Live API

4. **No Questions Available**
   - Verify `scraped_questions` collection has data
   - Verify `generated_skills` collection has skills
   - Check DASH API logs for warnings

5. **Authentication Fails**
   - Verify Google OAuth credentials
   - Check JWT_SECRET matches across services
   - Verify token expiration

### Debug Mode

Enable debug logging by setting log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## License

[Add your license information here]

---

## Contributing

[Add contributing guidelines here]

---

## Support

For issues and questions:
1. Check logs in `logs/` directory
2. Review service health endpoints
3. Check MongoDB connection and data
4. Review deployment documentation

---

**Last Updated**: 2025-01-27
**Version**: 1.1.0

## Recent Updates

### Version 1.1.0 (2025-01-27)
- **Tutor Service Migration**: Moved from backend WebSocket proxy to frontend direct integration with Gemini Live API
- **Feed Webhook System**: Added real-time feed webhook for media mixer, audio input, and transcripts
- **Instruction Injection**: Added dynamic instruction injection to tutor based on feed analysis
- **Architecture Simplification**: Removed backend Tutor service from deployment pipeline

