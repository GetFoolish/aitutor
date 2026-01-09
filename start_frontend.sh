#!/bin/bash
# Start frontend with proper Node.js version

cd "$(dirname "$0")/frontend"

# Try to use nvm if available
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
    # Try Node 20 first, then 22
    if nvm list 20 2>/dev/null | grep -q "v20"; then
        nvm use 20
        echo "✅ Using Node.js $(node --version) via nvm"
    elif nvm list 22 2>/dev/null | grep -q "v22"; then
        nvm use 22
        echo "✅ Using Node.js $(node --version) via nvm"
    else
        echo "⚠️  Node.js 20 or 22 not found in nvm. Installing Node 20..."
        nvm install 20
        nvm use 20
        echo "✅ Installed and using Node.js $(node --version)"
    fi
else
    # Check if system Node.js is compatible
    NODE_VERSION=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
    if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" -lt 20 ]; then
        echo "❌ Node.js version too old: $(node --version 2>/dev/null || echo 'unknown')"
        echo "   Required: Node.js 20.19+ or 22.12+"
        echo ""
        echo "   Install nvm:"
        echo "   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
        echo ""
        echo "   Then:"
        echo "   nvm install 20"
        echo "   nvm use 20"
        exit 1
    fi
    echo "✅ Using system Node.js $(node --version)"
fi

echo "Starting frontend..."
npm run dev

