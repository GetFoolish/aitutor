#!/usr/bin/env python3
"""
Homework API End-to-End Test Script

Run this BEFORE claiming the homework feature works.
Tests the actual HTTP endpoints, not internal functions.

Usage: python scripts/test_homework_api.py
"""

import requests
import sys
import os

BASE_URL = os.getenv("API_BASE_URL", "http://localhost")
AUTH_PORT = 8003
HOMEWORK_PORT = 8004

def test_services_up():
    """Check both services are running"""
    print("1. Checking services are up...")
    
    try:
        r = requests.get(f"{BASE_URL}:{AUTH_PORT}/health", timeout=5)
        assert r.status_code == 200, f"Auth service not healthy: {r.status_code}"
        print(f"   ✓ Auth service (:{AUTH_PORT}) healthy")
    except Exception as e:
        print(f"   ✗ Auth service failed: {e}")
        return False
    
    try:
        r = requests.get(f"{BASE_URL}:{HOMEWORK_PORT}/health", timeout=5)
        assert r.status_code == 200, f"Homework service not healthy: {r.status_code}"
        print(f"   ✓ Homework service (:{HOMEWORK_PORT}) healthy")
    except Exception as e:
        print(f"   ✗ Homework service failed: {e}")
        return False
    
    return True

def test_auth_flow():
    """Test signup and get token"""
    print("\n2. Testing auth flow...")
    
    import random
    email = f"test{random.randint(1000,9999)}@test.com"
    
    signup_data = {
        "email": email,
        "password": "TestPass123!",
        "name": "API Test User",
        "date_of_birth": "2010-01-01",
        "country": "US",
        "gender": "Other",
        "preferred_language": "English"
    }
    
    r = requests.post(f"{BASE_URL}:{AUTH_PORT}/auth/signup", json=signup_data)
    if r.status_code != 200:
        print(f"   ✗ Signup failed: {r.status_code} - {r.text[:200]}")
        return None
    
    token = r.json().get("token")
    if not token:
        print(f"   ✗ No token in response: {r.json()}")
        return None
    
    print(f"   ✓ Signup successful, got JWT token")
    return token

def test_homework_list(token):
    """Test listing homework"""
    print("\n3. Testing homework list...")
    
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}:{HOMEWORK_PORT}/homework/list", headers=headers)
    
    if r.status_code != 200:
        print(f"   ✗ List failed: {r.status_code} - {r.text[:200]}")
        return False
    
    data = r.json()
    print(f"   ✓ List returned {data.get('total', 0)} items")
    return True

def test_homework_upload(token):
    """Test uploading a file"""
    print("\n4. Testing homework upload...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with text file
    test_content = b"3 + 4 = ___\n5 + 2 = ___\n8 - 3 = ___"
    files = {"file": ("test_math.txt", test_content, "text/plain")}
    
    r = requests.post(
        f"{BASE_URL}:{HOMEWORK_PORT}/homework/upload",
        headers=headers,
        files=files
    )
    
    if r.status_code not in [200, 201]:
        print(f"   ✗ Upload failed: {r.status_code} - {r.text[:200]}")
        return None
    
    homework_id = r.json().get("homework_id")
    print(f"   ✓ Upload successful: {homework_id}")
    return homework_id

def test_homework_details(token, homework_id):
    """Test getting homework details and extracted text"""
    print("\n5. Testing homework details...")
    
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        f"{BASE_URL}:{HOMEWORK_PORT}/homework/{homework_id}",
        headers=headers
    )
    
    if r.status_code != 200:
        print(f"   ✗ Get details failed: {r.status_code} - {r.text[:200]}")
        return False
    
    data = r.json()
    extracted_text = data.get("extracted_text", "")
    
    if not extracted_text:
        print(f"   ✗ No extracted text!")
        return False
    
    print(f"   ✓ Got extracted text: {extracted_text[:50]}...")
    return True

def test_homework_delete(token, homework_id):
    """Test deleting homework"""
    print("\n6. Testing homework delete...")
    
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.delete(
        f"{BASE_URL}:{HOMEWORK_PORT}/homework/{homework_id}",
        headers=headers
    )
    
    if r.status_code != 200:
        print(f"   ✗ Delete failed: {r.status_code} - {r.text[:200]}")
        return False
    
    print(f"   ✓ Deleted successfully")
    return True

def main():
    print("=" * 50)
    print("HOMEWORK API END-TO-END TEST")
    print("=" * 50)
    
    # Run all tests
    if not test_services_up():
        print("\n❌ FAILED: Services not running")
        sys.exit(1)
    
    token = test_auth_flow()
    if not token:
        print("\n❌ FAILED: Auth flow broken")
        sys.exit(1)
    
    if not test_homework_list(token):
        print("\n❌ FAILED: List endpoint broken")
        sys.exit(1)
    
    homework_id = test_homework_upload(token)
    if not homework_id:
        print("\n❌ FAILED: Upload endpoint broken")
        sys.exit(1)
    
    if not test_homework_details(token, homework_id):
        print("\n❌ FAILED: Details endpoint broken")
        sys.exit(1)
    
    if not test_homework_delete(token, homework_id):
        print("\n❌ FAILED: Delete endpoint broken")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED")
    print("=" * 50)
    print("\nThe homework API is working end-to-end.")
    sys.exit(0)

if __name__ == "__main__":
    main()
