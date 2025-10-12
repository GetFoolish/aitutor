# Teaching Assistant Integration - Testing Guide

## Overview
This document explains how to verify the Teaching Assistant is fully integrated and working.

## Files Created/Modified

### Backend Files (NEW)
1. **`backend/ta_server.py`** - Main TA WebSocket server
   - Receives Gemini responses from frontend
   - Runs emotional intelligence, context provider, performance tracking
   - Sends prompt injections back to frontend

### Frontend Files (NEW/MODIFIED)
1. **`frontend/src/lib/teaching-assistant-bridge.ts`** - TA Bridge client
   - Connects to TA WebSocket server
   - Forwards Gemini messages to TA
   - Receives TA prompt injections and sends to Gemini

2. **`frontend/src/App.tsx`** - Modified to initialize TA Bridge
   - Creates TeachingAssistantBridge instance
   - Attaches to Gemini client
   - Manages TA connection lifecycle

### Configuration Files (MODIFIED)
1. **`run_tutor.sh`** - Updated startup script
   - Now starts TA server on port 9000
   - Creates logs/ta_server.log

2. **`frontend/src/hooks/use-live-api.ts`** - Model upgraded
   - Changed from `models/gemini-2.0-flash-exp`
   - To `models/gemini-2.5-flash-live`

3. **`frontend/src/components/altair/Altair.tsx`** - Model upgraded
4. **`frontend/README.md`** - Documentation updated

## Validation Steps

### Step 1: Run Validation Script
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
./validate_integration.sh
```

**Expected Output:**
- All files should be found (✓)
- All integration points should pass (✓)
- "✅ All checks passed!"

### Step 2: Check Backend Dependencies
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
/Users/vandanchopra/Vandan_Personal_Folder/CODE_STUFF/Projects/venvs/aitutor/bin/python -c "import websockets, chromadb, networkx; print('✓ All dependencies installed')"
```

### Step 3: Test TA Server Standalone
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
/Users/vandanchopra/Vandan_Personal_Folder/CODE_STUFF/Projects/venvs/aitutor/bin/python backend/ta_server.py
```

**Expected Output:**
```
============================================================
Teaching Assistant Server Starting...
============================================================
Initializing Teaching Assistant components...
✅ All TA components initialized
Starting WebSocket server on localhost:9000
✅ Teaching Assistant listening on ws://localhost:9000
Waiting for frontend connections...
```

Press `Ctrl+C` to stop, then continue.

### Step 4: Start Full System
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
./run_tutor.sh
```

**Expected Output:**
```
Starting Python backend... Logs -> logs/mediamixer.log
Starting DASH API server... Logs -> logs/api.log
🤖 Starting Teaching Assistant server... Logs -> logs/ta_server.log
Waiting for backend services to initialize...
Starting Node.js frontend... Logs -> logs/frontend.log

======================================
✅ AI Tutor is running!
======================================
Services:
  - MediaMixer (Port 8765)
  - DASH API (Port 8000)
  - Teaching Assistant (Port 9000) 🤖
  - Frontend (Port 3000)
```

### Step 5: Monitor TA Server Logs
In a **new terminal**:
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
tail -f logs/ta_server.log
```

**What to look for:**
1. Server startup messages
2. "Frontend connected" when you open the app
3. "Received Gemini response" when Adam talks
4. "TA Injecting prompt" when TA intervenes

### Step 6: Test in Browser

1. **Open**: http://localhost:3000
2. **Open Browser Console**: F12 → Console tab
3. **Start a session**: Click "Connect" or similar button
4. **Send a message** to Adam

**Expected Console Output:**
```
[TA Bridge] Initializing...
[TA Bridge] Connecting to ws://localhost:9000...
[TA Bridge] ✅ Connected to Teaching Assistant
[TA Bridge] Attached to Gemini client
[TA Bridge] Teaching Assistant connected
```

When Adam responds:
```
[TA Bridge] Forwarded Gemini response to TA (245 chars)
[TA Bridge] ℹ️ TA captured: Let's explore this problem together...
```

When TA intervenes:
```
[TA Bridge] 🤖 Injecting TA prompt: Welcome back, Student! I'm excited...
```

### Step 7: Verify TA Functionality

**Test Greeting:**
- Start session → TA should send greeting within 3 seconds
- Check console for: "TA → Adam: Welcome back..."

**Test Inactivity Monitor:**
- Wait 60 seconds without interaction
- TA should send nudge: "Hey, are you still there?"

**Test Emotional Intelligence:**
- Have conversation with 5+ messages
- Check logs for: "Running emotional intelligence analysis..."

**Test Context Provider:**
- Have conversation with 10+ messages
- Check logs for: "Fetching historical context..."

## Verification Checklist

- [ ] Validation script passes all checks
- [ ] TA server starts without errors
- [ ] Full system starts all 4 services
- [ ] Browser console shows TA Bridge connected
- [ ] TA logs show "Frontend connected"
- [ ] TA logs show "Received Gemini response" when Adam talks
- [ ] TA logs show "TA Injecting prompt" when TA intervenes
- [ ] Greeting appears within 3 seconds of session start
- [ ] Inactivity nudge appears after 60 seconds of silence

## Troubleshooting

### Issue: TA server won't start
**Check:** Missing dependencies
```bash
pip install chromadb networkx websockets sentence-transformers
```

### Issue: Frontend doesn't connect to TA
**Check:** Port 9000 blocked
```bash
lsof -i :9000  # See what's using port 9000
```

### Issue: No TA logs in console
**Check:** Browser console for errors
- Look for WebSocket connection errors
- Check if TA Bridge initialization failed

### Issue: TA doesn't inject prompts
**Check:** TA server logs
```bash
grep "Injecting prompt" logs/ta_server.log
```

If empty, TA might not be analyzing messages correctly.

## Success Criteria

✅ **Integration is successful if:**
1. All 4 services start without errors
2. TA Bridge connects to backend (console log)
3. TA server receives Gemini responses (server log)
4. TA injects at least greeting prompt (visible in Adam's response or console)
5. No WebSocket errors in browser console

## Key Log Files

- `logs/ta_server.log` - TA backend activity
- `logs/frontend.log` - React app output
- `logs/api.log` - DASH API
- `logs/mediamixer.log` - MediaMixer backend

## Next Steps After Validation

Once validated, you should see:
- TA greeting when session starts
- TA analyzing every Gemini response
- TA providing emotional intelligence insights
- TA surfacing historical context
- TA tracking performance metrics

All WITHOUT any hardcoded behaviors - this is the REAL system running.
