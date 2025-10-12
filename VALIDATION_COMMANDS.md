# Quick Validation Commands

Run these commands in your terminal to validate the integration.

## 1. Navigate to Project
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
```

## 2. Run Validation Script
```bash
./validate_integration.sh
```
**Expected:** All checks pass (green checkmarks)

## 3. Check Key Files Exist
```bash
# Backend TA Server
ls -lh backend/ta_server.py

# Frontend TA Bridge
ls -lh frontend/src/lib/teaching-assistant-bridge.ts

# Modified App.tsx
grep -n "TeachingAssistantBridge" frontend/src/App.tsx

# Updated run_tutor.sh
grep -n "ta_server.py" run_tutor.sh
```

## 4. Verify Model Upgrade
```bash
# Should show: models/gemini-2.5-flash-live
grep "gemini-2.5" frontend/src/hooks/use-live-api.ts
grep "gemini-2.5" frontend/src/components/altair/Altair.tsx
```

## 5. Test TA Server Standalone (Optional)
```bash
# This will start just the TA server
# Press Ctrl+C to stop after you see "✅ Teaching Assistant listening"
/Users/vandanchopra/Vandan_Personal_Folder/CODE_STUFF/Projects/venvs/aitutor/bin/python backend/ta_server.py
```

## 6. Start Full System
```bash
./run_tutor.sh
```

## 7. In Another Terminal - Watch TA Logs
```bash
cd "/Users/gagan/Desktop/gagan_projects/teaching assistant/aitutor"
tail -f logs/ta_server.log
```

## 8. Open Browser and Check Console
1. Open: http://localhost:3000
2. Press F12 → Console tab
3. Look for:
   - `[TA Bridge] Initializing...`
   - `[TA Bridge] ✅ Connected to Teaching Assistant`
   - `[TA Bridge] Attached to Gemini client`

## 9. Verify Integration Points

### Check Frontend sends to Backend
```bash
# In TA logs, look for:
grep "Received Gemini response" logs/ta_server.log
```

### Check Backend sends to Frontend
```bash
# In TA logs, look for:
grep "Injecting prompt" logs/ta_server.log
```

### Check Browser Console for TA Activity
Open browser console and look for:
- `[TA Bridge] Forwarded Gemini response to TA`
- `[TA Bridge] 🤖 Injecting TA prompt`

## Files to Check in Your Terminal

```bash
# 1. TA Server exists and is executable
file backend/ta_server.py

# 2. TA Bridge is integrated
head -30 frontend/src/App.tsx | grep -A 5 "TeachingAssistantBridge"

# 3. run_tutor.sh includes TA server
grep -A 2 "Teaching Assistant" run_tutor.sh

# 4. Model upgrade completed
grep -n "2.5-flash-live" frontend/src/hooks/use-live-api.ts
grep -n "2.5-flash-live" frontend/src/components/altair/Altair.tsx

# 5. TA components exist
ls -lh backend/teaching_assistant/*.py

# 6. Memory components exist
ls -lh backend/memory/*.py
```

## Success Indicators

✅ **You'll know it's working when you see:**

1. **In terminal where run_tutor.sh runs:**
   ```
   🤖 Starting Teaching Assistant server... Logs -> logs/ta_server.log
   ✅ AI Tutor is running!
   ```

2. **In TA server logs (`tail -f logs/ta_server.log`):**
   ```
   Teaching Assistant Server Starting...
   ✅ Teaching Assistant listening on ws://localhost:9000
   🔌 Frontend connected from ...
   📨 Received Gemini response (245 chars)
   🤖 TA Injecting prompt: Welcome back, Student!
   ```

3. **In browser console (F12):**
   ```
   [TA Bridge] ✅ Connected to Teaching Assistant
   [TA Bridge] Attached to Gemini client
   [TA Bridge] Forwarded Gemini response to TA (123 chars)
   [TA Bridge] 🤖 Injecting TA prompt: ...
   ```

## Quick Debug Commands

### If TA server won't start:
```bash
# Check for missing dependencies
/Users/vandanchopra/Vandan_Personal_Folder/CODE_STUFF/Projects/venvs/aitutor/bin/python -c "import websockets, chromadb, networkx, sentence_transformers; print('All deps OK')"
```

### If frontend won't connect:
```bash
# Check if TA server is running
lsof -i :9000

# Check TA server logs for errors
cat logs/ta_server.log | grep -i error
```

### If no TA activity visible:
```bash
# Check if messages are being forwarded
grep "Forwarded Gemini response" logs/ta_server.log
grep "Received Gemini response" logs/ta_server.log
```

## The Proof

Run this to see the integration working:
```bash
# Start system
./run_tutor.sh &

# Wait 5 seconds
sleep 5

# Check TA server is running
ps aux | grep ta_server.py

# Check TA server logs show initialization
head -20 logs/ta_server.log

# Check TA server is listening
lsof -i :9000
```

No hardcoded demos. No fake responses. This is the REAL integrated system.
