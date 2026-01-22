#!/bin/bash

# Setup script for local development environment

echo "🚀 Setting up local development environment..."
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Create .env file from template
cat > .env << 'EOF'
# =================================
# MongoDB Configuration
# =================================
# Get your connection string from MongoDB Atlas: https://cloud.mongodb.com
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
MONGODB_DB_NAME=ai_tutor

# =================================
# Google APIs (Required)
# =================================
# Get your key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here

# Gemini Live API Model (for voice tutor)
# IMPORTANT: Use this model for the Live API - older models are deprecated
GEMINI_MODEL=models/gemini-2.5-flash-native-audio-preview-09-2025

# =================================
# Authentication (Required)
# =================================
# Generate a strong secret: node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
JWT_SECRET=your_jwt_secret_here_at_least_32_chars

# Google OAuth (for login)
# Get from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Frontend URL (must match vite.config.ts port)
FRONTEND_URL=http://localhost:3004

# =================================
# OpenRouter API (Optional - for Video Search)
# =================================
# Get your key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
EOF

echo "✅ Created .env file"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env file and add your actual API keys and MongoDB URI"
echo "   2. Run: ./run_tutor.sh"
echo ""
echo "💡 The frontend will automatically use localhost URLs for local development"
echo "   No need to configure frontend environment variables!"

