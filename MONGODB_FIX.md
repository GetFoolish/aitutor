# MongoDB Connection Fix

## Problem
Backend was defaulting to localhost:27017 instead of Atlas, causing timeouts and breaking all database operations.

## Root Cause
`mongodb_manager.py` has `MONGODB_PREFER_LOCAL=true` as default, which tries localhost first.

## Solution
Add to `.env`:
```
MONGODB_PREFER_LOCAL=false
```

This ensures Atlas connection is tried first (and is the only option in environments without local MongoDB).

## Verification
Backend logs should show:
```
[MONGODB] Attempting connection using mongodb+srv://***@cluster0.zbntx5t.mongodb.net/...
[MONGODB] Connected to database: ai_tutor
```

NOT:
```
[MONGODB] Attempting connection using mongodb://localhost:27017/ai_tutor
```
