#!/bin/bash
# Quick start script that handles Node.js version

echo "🚀 Quick Start Script"
echo "===================="
echo ""

# Load nvm if available
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    echo "📦 Loading nvm..."
    source "$HOME/.nvm/nvm.sh"
    
    # Check if Node 20 or 22 is available
    if nvm list 20 2>/dev/null | grep -q "v20" || nvm list 22 2>/dev/null | grep -q "v22"; then
        if nvm list 20 2>/dev/null | grep -q "v20"; then
            echo "✅ Using Node.js 20"
            nvm use 20
        else
            echo "✅ Using Node.js 22"
            nvm use 22
        fi
    else
        echo "⚠️  Node.js 20/22 not found. Installing Node 20..."
        nvm install 20
        nvm use 20
    fi
    echo "   Node.js version: $(node --version)"
    echo ""
fi

# Check Node.js version
NODE_MAJOR=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 20 ]; then
    echo "❌ Node.js version too old: $(node --version 2>/dev/null || echo 'unknown')"
    echo "   Please install Node.js 20+ using nvm:"
    echo "   source ~/.nvm/nvm.sh && nvm install 20 && nvm use 20"
    exit 1
fi

echo "✅ Node.js version OK: $(node --version)"
echo ""
echo "Starting services..."
echo ""

# Start backend services
./run_tutor.sh
