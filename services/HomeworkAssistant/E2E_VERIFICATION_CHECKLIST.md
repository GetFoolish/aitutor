# End-to-End Verification Checklist
## Homework Upload and AI Assistance Feature

**Date:** 2026-01-16
**Subtask:** subtask-3-4
**Services:** HomeworkAssistant (port 8004), Frontend (port 3000)

---

## Prerequisites

✅ **Backend Service**: HomeworkAssistant running on port 8004
- Health check: `curl http://localhost:8004/health`
- Expected: `{"status":"healthy","service":"HomeworkAssistant"}`

✅ **Frontend Service**: React app running on port 3000
- URL: http://localhost:3000
- User must be logged in with valid JWT token

✅ **Test Files**: Have a sample PDF file ready for testing
- File should be less than 10MB
- Recommended: A simple homework assignment or study material

---

## Verification Steps

### 1. ✅ Start Backend Service on Port 8004
**Status:** COMPLETED
**Command:** `python -m uvicorn api:app --host 0.0.0.0 --port 8004 --reload`
**Verification:** Service is running and health endpoint responds correctly

---

### 2. ✅ Start Frontend on Port 3000
**Status:** COMPLETED
**Verification:** Frontend is accessible at http://localhost:3000

---

### 3. ⏳ Open FloatingControlPanel
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Navigate to http://localhost:3000 in your browser
2. Ensure you are logged in (JWT token is valid)
3. Locate the FloatingControlPanel (should be visible on the screen)
4. The panel should show control buttons

**Expected Result:**
- FloatingControlPanel is visible and responsive
- No console errors in browser DevTools

---

### 4. ⏳ Click Homework Button (BookOpen Icon)
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Look for the Homework button with a BookOpen (📖) icon
2. Click the button to open the HomeworkPanel popover

**Expected Result:**
- HomeworkPanel popover opens smoothly
- Panel shows three tabs: "Upload", "My Homework", "Chat"
- Default tab is "Upload"
- Panel has neo-brutalist styling with thick borders and shadows

---

### 5. ⏳ Drag and Drop PDF File
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Ensure "Upload" tab is active
2. Drag a PDF file from your file system
3. Drop it onto the upload area

**Alternative:** Click the upload area to open file picker

**Expected Result:**
- Drag area shows visual feedback during drag
- File is accepted (PDF, JPG, PNG, DOCX, TXT)
- File size validation: max 10MB
- File preview shows file icon, name, and size

---

### 6. ⏳ Verify File Uploads Successfully
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. After dropping the file, click "Upload Homework" button
2. Watch for upload progress indicator
3. Wait for upload completion

**Expected Result:**
- Progress bar shows upload percentage
- Upload completes successfully (no errors)
- Success message appears
- View automatically switches to "My Homework" tab

**Backend Verification:**
- MongoDB should have new document in `homework` collection
- GridFS should have the uploaded file

---

### 7. ⏳ Check Homework Appears in My Homework List
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Navigate to "My Homework" tab (if not auto-switched)
2. Look for the uploaded homework in the list

**Expected Result:**
- Homework item appears in the list
- Shows correct file name
- Shows upload date and time
- Shows file type icon (PDF, image, text, etc.)
- Shows file size
- Thumbnail preview visible (for images/PDFs)

---

### 8. ⏳ Click on Homework Item
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Click on the homework item in the list
2. View should switch to "Chat" tab

**Expected Result:**
- Chat tab opens automatically
- Empty state shows if no previous conversation
- Suggested questions appear (optional)
- Input field is ready for questions

---

### 9. ⏳ Ask AI a Question About the Homework
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. In the Chat tab, type a question about the homework
2. Example: "Can you summarize this document?" or "What is the main topic?"
3. Press Enter or click Send button

**Expected Result:**
- Question appears in the chat as user message (right side, purple background)
- Loading indicator appears (animated dots: "AI is thinking...")
- No console errors

---

### 10. ⏳ Verify AI Provides Relevant Response
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Wait for AI response (may take 2-10 seconds)
2. Read the AI's response

**Expected Result:**
- AI response appears in chat (left side, yellow background)
- Response is relevant to the uploaded homework content
- Response demonstrates understanding of the document
- Timestamp is shown for the message
- No error messages or API failures

**Technical Validation:**
- Check Network tab: POST to `/homework/assist` should return 200
- Response includes `response`, `homework_id`, `timestamp` fields

---

### 11. ⏳ Ask Follow-up Question
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Type a follow-up question that references the previous conversation
2. Example: "Can you explain that in simpler terms?" or "What about section 2?"
3. Send the question

**Expected Result:**
- New question appears in chat
- AI responds again
- Loading indicator shows while processing

---

### 12. ⏳ Verify Conversation Context is Maintained
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Check if AI's follow-up response references previous conversation
2. Reload the page or close/reopen the panel
3. Check if conversation history persists

**Expected Result:**
- AI understands context from previous messages
- Follow-up responses are coherent and contextual
- After page reload, conversation history is still visible
- All previous messages are displayed in correct order

**Technical Validation:**
- Check Network tab: GET to `/homework/{id}` includes `conversation_history`
- MongoDB document should have `conversation_history` array with all turns

---

### 13. ⏳ Delete Homework and Verify It's Removed
**Status:** PENDING MANUAL VERIFICATION
**Steps:**
1. Navigate back to "My Homework" tab
2. Find the delete button (trash icon) for the homework item
3. Click delete
4. Confirm deletion if prompted
5. Check the list updates

**Expected Result:**
- Confirmation dialog appears (if implemented)
- After confirming, homework disappears from list
- Success message appears
- List updates immediately (no page reload needed)
- If it was the last item, empty state appears

**Backend Verification:**
- MongoDB document should be deleted
- GridFS file should be removed
- Verify with: No document in `homework` collection with that ID

---

## Additional Checks

### Browser Console
- [ ] No JavaScript errors
- [ ] No network errors (check Network tab)
- [ ] No React warnings

### Performance
- [ ] Upload completes in reasonable time (< 30s for 10MB file)
- [ ] AI responses arrive within 10 seconds
- [ ] UI remains responsive during operations

### Edge Cases
- [ ] Test with different file types (PDF, JPG, PNG, TXT, DOCX)
- [ ] Test file size limit (try uploading 11MB file, should fail gracefully)
- [ ] Test unsupported file type (should show error message)
- [ ] Test with network disconnect (should handle gracefully)

---

## Backend API Verification (Automated)

```bash
# Health check
curl http://localhost:8004/health
# Expected: {"status":"healthy","service":"HomeworkAssistant"}

# List endpoint (requires auth - expect 401)
curl -X GET http://localhost:8004/homework/list
# Expected: 401 Unauthorized (without token)

# With valid token (replace YOUR_JWT_TOKEN)
curl -X GET http://localhost:8004/homework/list \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
# Expected: {"homework_items":[],"total":0} (if no homework uploaded yet)
```

---

## Success Criteria

All the following must be true to mark this subtask as COMPLETED:

1. ✅ Backend and frontend services are running
2. ⏳ User can open HomeworkPanel from FloatingControlPanel
3. ⏳ User can upload a file via drag-and-drop or file picker
4. ⏳ Uploaded homework appears in "My Homework" list with correct metadata
5. ⏳ User can click homework to open chat interface
6. ⏳ User can ask questions and receive relevant AI responses
7. ⏳ Follow-up questions maintain conversation context
8. ⏳ Conversation history persists across page reloads
9. ⏳ User can delete homework and it's removed from list and database
10. ⏳ No console errors or UI breaking bugs

---

## Known Issues / Notes

- File preview for PDFs requires the backend to serve the file via `/homework/{id}/file` endpoint
- AI responses depend on Google Gemini API (ensure GOOGLE_API_KEY is set in environment)
- MongoDB must be running and accessible
- JWT token must be valid (check localStorage in DevTools)

---

## Next Steps After Verification

If all checks pass:
1. Mark this subtask as "completed" in implementation_plan.json
2. Commit changes with message: "auto-claude: subtask-3-4 - End-to-end verification of full homework workflow"
3. Proceed to Phase 4 (Polish) subtasks for error handling and UX improvements

If any checks fail:
1. Document the failure in build-progress.txt
2. Create GitHub issue or fix immediately
3. Re-run verification after fixes
