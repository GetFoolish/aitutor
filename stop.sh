#!/bin/bash

# =================================
# AI Tutor - Stop All Services
# =================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }

echo "======================================"
echo "   Stopping AI Tutor Services"
echo "======================================"
echo ""

# Stop services using PID files
if [ -d "logs" ]; then
    for pidfile in logs/*.pid; do
        if [ -f "$pidfile" ]; then
            service_name=$(basename "$pidfile" .pid)
            pid=$(cat "$pidfile")

            if ps -p $pid > /dev/null 2>&1; then
                print_info "Stopping $service_name (PID: $pid)..."
                kill $pid
                sleep 1

                # Force kill if still running
                if ps -p $pid > /dev/null 2>&1; then
                    kill -9 $pid
                fi

                rm "$pidfile"
                print_success "$service_name stopped"
            else
                print_info "$service_name was not running"
                rm "$pidfile"
            fi
        fi
    done
fi

# Fallback: kill by process name
print_info "Cleaning up any remaining processes..."
pkill -f "auth_api.py" 2>/dev/null && print_success "Stopped auth service"
pkill -f "services/HomeworkAssistant/api.py" 2>/dev/null && print_success "Stopped homework service"
pkill -f "vite" 2>/dev/null && print_success "Stopped frontend"

echo ""
print_success "All services stopped"
echo ""
