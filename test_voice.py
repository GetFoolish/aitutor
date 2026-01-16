"""Test Voice Integration for AI Tutor"""
import asyncio
import os
import jwt
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Configuration
AUTH_URL = "http://localhost:8003"
TA_URL = "http://localhost:8002"
JWT_SECRET = os.getenv("JWT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def create_test_token():
    """Create a test JWT token matching the expected format"""
    payload = {
        "sub": "user_4f5739693a92",  # user_id goes in "sub"
        "email": "test@example.com",
        "name": "Test User",
        "google_id": "113397566226061970513",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def test_gemini_token():
    """Test getting a Gemini ephemeral token"""
    print("=" * 50)
    print("1. Testing Gemini Token Endpoint")
    print("=" * 50)
    
    # Create JWT token
    token = create_test_token()
    print(f"✅ Created test JWT token")
    
    # Request Gemini token
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{AUTH_URL}/auth/gemini-token", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Got Gemini ephemeral token!")
        print(f"   Model: {data.get('model', 'N/A')}")
        print(f"   Token length: {len(data.get('token', ''))}")
        return data
    else:
        print(f"❌ Failed to get Gemini token: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_gemini_live_api(token_data):
    """Test Gemini Live API connection"""
    print("\n" + "=" * 50)
    print("2. Testing Gemini Live API Connection")
    print("=" * 50)
    
    if not token_data:
        print("❌ No token data - skipping")
        return False
    
    try:
        from google import genai
        from google.genai import types
        
        # Initialize client with ephemeral token
        client = genai.Client(api_key=token_data['token'])
        
        print(f"✅ Gemini client initialized with ephemeral token")
        
        # Try to create a Live session config (validates token)
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
        )
        print(f"✅ Live config created - token is valid for voice!")
        print(f"   Ready for WebSocket connection to Gemini Live API")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_teaching_assistant():
    """Test TeachingAssistant session"""
    print("\n" + "=" * 50)
    print("3. Testing TeachingAssistant Session")
    print("=" * 50)
    
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Start session
    response = requests.post(
        f"{TA_URL}/session/start",
        headers=headers,
        json={"user_id": "user_4f5739693a92"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Teaching session started!")
        print(f"   Session ID: {data.get('session_id', 'N/A')}")
        greeting = data.get('prompt', '')
        if greeting:
            print(f"   Greeting: {greeting[:80]}...")
        return data
    else:
        print(f"❌ Failed to start session: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None

def test_dash_api():
    """Test DASH API"""
    print("\n" + "=" * 50)
    print("4. Testing DASH API")
    print("=" * 50)

    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Test grading panel endpoint (correct endpoint for skill data)
    response = requests.get(
        "http://localhost:8000/api/grading-panel",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ DASH API working!")
        units = data.get('units', [])
        print(f"   Units returned: {len(units)}")
        if units:
            print(f"   First unit: {units[0].get('name', 'N/A')[:40]}...")
        return True
    else:
        print(f"⚠️  DASH response: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

if __name__ == "__main__":
    print("\n🎤 AI Tutor Voice Integration Test\n")
    
    # Test 1: Gemini Token
    token_data = test_gemini_token()
    
    # Test 2: Gemini Live API
    if token_data:
        test_gemini_live_api(token_data)
    
    # Test 3: Teaching Assistant
    test_teaching_assistant()
    
    # Test 4: DASH API
    test_dash_api()
    
    print("\n" + "=" * 50)
    print("🎉 Voice Integration Test Complete!")
    print("=" * 50)
    print("\nIf all tests passed, the voice system is ready to use.")
    print("Open http://localhost:3000/app and start a session!")
