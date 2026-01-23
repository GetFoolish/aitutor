# Testing as Maya - Developer Guide

This guide explains how to test the AI Tutor memory system using Maya's pre-populated memories.

## Who is Maya?

Maya Chen is a test persona with 25 pre-loaded memories simulating 5 tutoring sessions:

| Attribute | Details |
|-----------|---------|
| **Name** | Maya Chen, 15 years old, 10th grade |
| **Location** | Portland, Oregon |
| **Pet** | Biscuit - 3yr old Corgi who steals socks |
| **Hobbies** | Soccer (midfielder), Digital art, Fantasy writing |
| **Family** | Dad (David, engineer), Mom (Sarah, nurse), Brother (Ethan, 11), Nai Nai (grandmother) |
| **Academic** | Struggles with math, visual learner, improved from 52% → 78% on quadratics |
| **Key Events** | ACL injury at 14, Nai Nai's stroke, Won Portland Art Museum competition |

## Quick Setup (2 minutes)

### Step 1: Add Test Mode to `.env`

Add this line to your `.env` file:

```bash
# Test Mode - Remove after testing
TEST_AS_USER=maya_final
```

### Step 2: Modify `shared/auth_middleware.py`

Replace the file contents with:

```python
"""
Shared JWT authentication middleware for FastAPI services
"""
import os
import jwt
from fastapi import Request, HTTPException
from typing import Optional, Dict
from shared.jwt_config import JWT_SECRET, JWT_ALGORITHM

# Test mode: Override user_id to test as Maya
TEST_AS_USER = os.getenv("TEST_AS_USER", "")  # Set to "maya_final" to test as Maya


def get_current_user(request: Request) -> str:
    """Extract and validate JWT token from request, return user_id"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header"
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")

        # TEST MODE: Override user_id if TEST_AS_USER is set
        if TEST_AS_USER:
            print(f"[TEST MODE] Overriding user_id from {user_id[:8]}... to {TEST_AS_USER}")
            return TEST_AS_USER

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_user_from_token(token: str) -> Optional[Dict]:
    """Extract user information from JWT token (for WebSocket connections)"""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        user_info = {
            "user_id": payload.get("sub"),
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "google_id": payload.get("google_id", "")
        }

        # TEST MODE: Override user_id if TEST_AS_USER is set
        if TEST_AS_USER:
            user_info["user_id"] = TEST_AS_USER
            user_info["name"] = "Maya Chen (Test Mode)"

        return user_info
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
```

### Step 3: Restart Teaching Assistant

```bash
# Kill existing process
lsof -ti:8002 | xargs kill -9

# Restart with test mode
source venv/bin/activate
source .env
python services/TeachingAssistant/api.py
```

### Step 4: Test

1. Open http://localhost:3000
2. Log in with any Google account
3. Start a tutoring session
4. The tutor should remember Maya's details!

## Test Prompts to Try

Ask the tutor about Maya's life to verify memories are working:

| Prompt | Expected Response |
|--------|-------------------|
| "How's Biscuit doing?" | Should know Biscuit is her corgi |
| "I have soccer practice today" | Should know she plays midfielder |
| "My grandma made cookies" | Should reference Nai Nai and her stroke recovery |
| "Remember that math test?" | Should know she improved from 52% to 78% |
| "I've been drawing lately" | Should know she won an art competition |

## Maya's Memories in MongoDB

```javascript
// Query to see Maya's memories
db.memories.find({ student_id: "maya_final" })
```

**Memory breakdown:**
- Personal: 6 (soccer, art, Biscuit, family)
- Academic: 2 (quadratics, game physics)
- Emotional: 17 (family dynamics, test anxiety, achievements)

## Disabling Test Mode

1. Remove `TEST_AS_USER=maya_final` from `.env`
2. Revert `shared/auth_middleware.py`:
   ```bash
   git checkout shared/auth_middleware.py
   ```
3. Restart the Teaching Assistant

## Alternative: Use the Simulator

For testing memory extraction without the UI:

```bash
python services/TeachingAssistant/Simulator.py --user_id maya_final
```

This runs simulated conversations and shows memory extraction in real-time.

---

**Note:** The `shared/auth_middleware.py` changes are intentionally NOT committed to the repo. Each developer should apply them locally for testing.
