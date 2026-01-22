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
# MongoDB Configuration
# Get your connection string from MongoDB Atlas: https://cloud.mongodb.com
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
MONGODB_DB_NAME=ai_tutor

# OpenRouter API Key
# Get your key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Google Gemini API Key
# Get your key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Gemini Model (has default)
GEMINI_MODEL=models/gemini-2.5-flash-native-audio-preview-09-2025
EOF

echo "✅ Created .env file"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env file and add your actual API keys and MongoDB URI"
echo "   2. Run: ./run_tutor.sh"
echo ""
echo "💡 The frontend will automatically use localhost URLs for local development"
echo "   No need to configure frontend environment variables!"

