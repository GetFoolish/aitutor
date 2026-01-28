#!/bin/bash

# =================================
# AI Tutor - Development Startup Script
# =================================
# This script starts all services required for local development
# Run with: ./dev.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

echo "======================================"
echo "   AI Tutor - Development Setup"
echo "======================================"
echo ""

# =================================
# Step 1: Check Prerequisites
# =================================
print_info "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi
print_success "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm."
    exit 1
fi
print_success "npm found: $(npm --version)"

# Check MongoDB (optional - can use Atlas)
if command -v mongod &> /dev/null; then
    print_success "MongoDB found locally"
else
    print_warning "MongoDB not found locally - make sure MONGODB_URI in .env points to a running instance"
fi

echo ""

# =================================
# Step 2: Check .env file
# =================================
print_info "Checking environment configuration..."

if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_info "Creating .env from .env.example..."
    cp .env.example .env
    print_warning "Please edit .env and add your API keys and configuration."
    print_info "At minimum, you need:"
    echo "  - GEMINI_API_KEY (for OCR and AI features)"
    echo "  - MONGODB_URI (for database)"
    echo "  - JWT_SECRET (for authentication)"
    echo "  - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (for Google OAuth)"
    echo ""
    print_error "After updating .env, run this script again: ./dev.sh"
    exit 1
fi

print_success ".env file found"

# Check critical environment variables
source .env
MISSING_VARS=()

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    MISSING_VARS+=("GEMINI_API_KEY")
fi

if [ -z "$MONGODB_URI" ] || [ "$MONGODB_URI" = "mongodb://localhost:27017/ai_tutor" ]; then
    print_warning "MONGODB_URI is using default localhost - make sure MongoDB is running"
fi

if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "your_secure_random_secret_here" ]; then
    MISSING_VARS+=("JWT_SECRET")
fi

if [ -z "$GOOGLE_CLIENT_ID" ] || [ "$GOOGLE_CLIENT_ID" = "your_google_oauth_client_id" ]; then
    MISSING_VARS+=("GOOGLE_CLIENT_ID")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    print_info "Please update your .env file with valid values."
    exit 1
fi

print_success "All required environment variables are set"
echo ""

# =================================
# Step 3: Setup Python Virtual Environment
# =================================
print_info "Setting up Python environment..."

if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
print_success "Python dependencies installed"

echo ""

# =================================
# Step 4: Setup Frontend Dependencies
# =================================
print_info "Setting up frontend dependencies..."

cd frontend

if [ ! -d "node_modules" ]; then
    print_info "Installing frontend dependencies (this may take a few minutes)..."
    npm install --silent
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies already installed"
fi

cd ..

echo ""

# =================================
# Step 5: Initialize Database
# =================================
print_info "Initializing database indexes..."
cd services/DashSystem
if python3 db_init.py; then
    print_success "Database indexes created"
else
    print_warning "Database initialization had issues (may already exist)"
fi
cd ../..

echo ""

# =================================
# Step 6: Start Services
# =================================
print_info "Starting services..."

# Create log directory
mkdir -p logs

# Function to start a service
start_service() {
    local name=$1
    local command=$2
    local port=$3
    local log_file="logs/${name}.log"

    print_info "Starting $name on port $port..."

    # Kill any existing process on the port
    lsof -ti:$port | xargs kill -9 2>/dev/null || true

    # Start the service
    eval "$command > $log_file 2>&1 &"
    local pid=$!

    # Wait a bit for service to start
    sleep 2

    # Check if service is running
    if ps -p $pid > /dev/null; then
        print_success "$name started (PID: $pid)"
        echo "$pid" > "logs/${name}.pid"
    else
        print_error "$name failed to start. Check $log_file for errors."
        tail -20 "$log_file"
        return 1
    fi
}

# Start Auth Service
start_service "auth-service" \
    "source venv/bin/activate && cd services/AuthService && python3 auth_api.py" \
    "${AUTH_SERVICE_PORT:-8003}"

# Start Homework Assistant Service
start_service "homework-service" \
    "source venv/bin/activate && cd services/HomeworkAssistant && python3 api.py" \
    "${HOMEWORK_SERVICE_PORT:-8004}"

# Start Frontend
start_service "frontend" \
    "cd frontend && npm run dev" \
    "${FRONTEND_PORT:-3000}"

echo ""

# =================================
# Step 7: Health Check
# =================================
print_info "Running health checks..."
sleep 3  # Give services time to initialize

if [ -f "scripts/monitor-services.sh" ]; then
    if bash scripts/monitor-services.sh; then
        print_success "All services passed health checks"
    else
        print_warning "Some services are slow or unhealthy - check logs"
    fi
else
    print_warning "Health monitor script not found, skipping checks"
fi

echo ""

# =================================
# Summary
# =================================
print_success "All services started successfully!"
echo ""
echo "======================================"
echo "   🎉 AI Tutor is Running!"
echo "======================================"
echo ""
echo "Services:"
echo "  • Frontend:          http://localhost:${FRONTEND_PORT:-3000}"
echo "  • Auth Service:      http://localhost:${AUTH_SERVICE_PORT:-8003}"
echo "  • Homework API:      http://localhost:${HOMEWORK_SERVICE_PORT:-8004}"
echo "  • API Documentation: http://localhost:${HOMEWORK_SERVICE_PORT:-8004}/docs"
echo ""
echo "Logs:"
echo "  • Auth:     tail -f logs/auth-service.log"
echo "  • Homework: tail -f logs/homework-service.log"
echo "  • Frontend: tail -f logs/frontend.log"
echo ""
echo "To stop all services: ./stop.sh"
echo ""
print_info "Open http://localhost:${FRONTEND_PORT:-3000} in your browser to get started!"
echo ""
