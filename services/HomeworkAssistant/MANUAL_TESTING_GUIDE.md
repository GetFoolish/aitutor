# Manual Testing Guide - Homework Feature
## Complete End-to-End Workflow Verification

**Status:** Ready for Manual Testing
**Date:** 2026-01-16
**Automated Checks:** ✅ All Passed (20/20)

---

## Prerequisites Verified ✅

- ✅ Backend (HomeworkAssistant) running on port 8004
- ✅ Frontend running on port 3000
- ✅ All API endpoints properly secured with JWT authentication
- ✅ All required files present (components, services, backend APIs)
- ✅ FloatingControlPanel integration complete

---

## Manual Testing Steps

### Step 1: Open the Application 🌐

1. Open your browser (Chrome or Firefox recommended)
2. Navigate to: **http://localhost:3000**
3. Open Developer Tools (F12 or Cmd+Option+I)
4. Check Console tab - should have no errors

**Expected:** Clean console, app loads successfully

---

### Step 2: Locate and Open Homework Panel 📖

1. Find the **FloatingControlPanel** (should be visible on the page)
2. Look for the **Homework button** with a **BookOpen** icon (📖)
3. Click the Homework button

**Expected:**
- HomeworkPanel popover opens
- Panel shows 3 tabs: "Upload", "My Homework", "Chat"
- Default tab is "Upload"
- Neo-brutalist styling with thick borders and shadows

**Screenshot Location:** Take a screenshot of opened panel

---

### Step 3: Upload a Homework File 📤

**Prepare a test file:**
- PDF file (recommended: a simple homework assignment, < 10MB)
- Alternative: JPG, PNG, TXT, or DOCX file

**Upload Methods:**

**Method A - Drag and Drop:**
1. Drag the file from your file system
2. Drop it onto the upload area in the "Upload" tab
3. Observe visual feedback during drag

**Method B - File Picker:**
1. Click on the upload area
2. Select file from the file picker dialog

**After selecting file:**
1. File preview appears showing icon, name, and size
2. Click "Upload Homework" button
3. Watch upload progress indicator

**Expected:**
- ✅ File is accepted (no errors)
- ✅ Progress bar shows percentage
- ✅ Upload completes successfully
- ✅ View switches to "My Homework" tab automatically
- ✅ No console errors

**Console Check:** Look for log: `Homework uploaded successfully: [homework_id]`

---

### Step 4: Verify Homework List 📋

In the "My Homework" tab:

**Check the following:**
- [ ] Uploaded homework appears in the list
- [ ] File name is correct
- [ ] Upload date/time is displayed
- [ ] File type icon is appropriate (PDF icon, image icon, etc.)
- [ ] File size is shown correctly
- [ ] Thumbnail preview visible (for images/PDFs)

**Expected:** All metadata displays correctly

---

### Step 5: Open Chat Interface 💬

1. Click on the homework item in the list
2. View should automatically switch to "Chat" tab

**Expected:**
- ✅ Chat tab opens
- ✅ If no previous conversation: empty state or suggested questions
- ✅ Chat input field is ready
- ✅ No console errors

---

### Step 6: Ask AI a Question 🤖

**Suggested Questions:**
- "Can you summarize this document?"
- "What is the main topic of this homework?"
- "Help me understand problem 1"
- "What are the key concepts?"

**Steps:**
1. Type your question in the input field
2. Press Enter or click Send

**Expected:**
- ✅ Question appears as user message (right side, purple background)
- ✅ Loading indicator shows: "AI is thinking..." with animated dots
- ✅ No console errors

**Network Tab Check:**
- POST request to `http://localhost:8004/homework/assist`
- Status: 200 OK
- Response includes: `response`, `homework_id`, `timestamp`

---

### Step 7: Verify AI Response 🎯

**Wait for AI response (typically 2-10 seconds)**

**Check the following:**
- [ ] AI response appears in chat (left side, yellow background)
- [ ] Response is relevant to the uploaded homework content
- [ ] Response demonstrates understanding of the document
- [ ] Timestamp is shown for the message
- [ ] No error messages

**Quality Check:**
- Does the AI reference specific content from your file?
- Is the response helpful and accurate?
- Is the formatting clean and readable?

---

### Step 8: Test Conversation Context 🔄

**Ask a follow-up question that requires context:**
- "Can you explain that in simpler terms?"
- "What about the next section?"
- "Can you give me an example?"

**Expected:**
- ✅ Follow-up question appears in chat
- ✅ AI responds with contextual awareness
- ✅ Response references previous conversation
- ✅ Loading indicator shows while processing

**Context Verification:**
- AI should understand what "that" or "it" refers to
- Response should build on previous conversation
- No repeated introductions or context loss

---

### Step 9: Test Persistence 💾

**Test conversation history persistence:**

1. **Refresh the page** (Cmd+R or F5)
2. Wait for app to reload
3. Open HomeworkPanel again
4. Navigate to "My Homework" tab
5. Click on the same homework item
6. Check "Chat" tab

**Expected:**
- ✅ All previous messages are still visible
- ✅ Messages appear in correct order (user/AI alternating)
- ✅ Timestamps are preserved
- ✅ Can continue conversation from where you left off

**Backend Verification:**
- Conversation should be stored in MongoDB
- GET request to `/homework/{id}` includes `conversation_history` array

---

### Step 10: Delete Homework 🗑️

1. Navigate back to "My Homework" tab
2. Find the delete button (trash icon) next to the homework
3. Click delete
4. If prompted, confirm deletion

**Expected:**
- ✅ Homework disappears from list immediately
- ✅ If last item: empty state appears ("No homework yet...")
- ✅ No console errors
- ✅ Success message or feedback

**Backend Verification:**
- DELETE request to `/homework/{id}` returns 200 OK
- MongoDB document is removed
- GridFS file is deleted

---

## Additional Test Scenarios

### Edge Case Testing 🧪

**Test 1: Large File (should fail gracefully)**
- Upload a file > 10MB
- Expected: Error message, upload prevented

**Test 2: Unsupported File Type**
- Upload a .exe or .zip file
- Expected: Error message, file rejected

**Test 3: Multiple Files**
- Upload 2-3 different homework files
- Expected: All appear in "My Homework" list
- Can switch between them in chat

**Test 4: Network Interruption**
- Start upload, then disable network
- Expected: Graceful error handling

**Test 5: Different File Types**
- Test with: PDF, JPG, PNG, TXT, DOCX
- Expected: All types upload and process correctly

---

## Performance Benchmarks ⚡

**Acceptable Performance:**
- File upload (1MB): < 5 seconds
- File upload (10MB): < 30 seconds
- AI response time: 2-10 seconds
- UI interactions: < 100ms (instant feel)
- Page load: < 2 seconds

**If performance is outside these ranges, note it as an issue.**

---

## Browser Console Checklist ✓

**Before marking complete, verify:**
- [ ] No JavaScript errors in Console
- [ ] No network errors (check Network tab)
- [ ] No React warnings about keys or hooks
- [ ] No CORS errors
- [ ] No 500 errors from backend
- [ ] All API calls return expected status codes

---

## Success Criteria Summary

**All must be TRUE to mark subtask as COMPLETED:**

1. ✅ Services running (backend on 8004, frontend on 3000)
2. ⏳ User can open HomeworkPanel from FloatingControlPanel
3. ⏳ File upload works (drag-and-drop and file picker)
4. ⏳ Homework appears in list with correct metadata
5. ⏳ Chat interface opens when clicking homework
6. ⏳ AI provides relevant responses to questions
7. ⏳ Follow-up questions maintain conversation context
8. ⏳ Conversation persists after page reload
9. ⏳ Delete functionality works correctly
10. ⏳ No console errors or breaking bugs

---

## Testing Completion Form

**Tester:** ___________________
**Date:** ___________________
**Time Spent:** ___________________

**Overall Result:**
- [ ] ✅ All tests passed - Ready to mark complete
- [ ] ⚠️ Minor issues found (document below)
- [ ] ❌ Major issues found (document below)

**Issues Found:**

```
Issue 1:
- Description:
- Severity: [Critical/Major/Minor]
- Steps to reproduce:

Issue 2:
- Description:
- Severity:
- Steps to reproduce:
```

**Screenshots/Evidence:**
- [ ] Homework panel opened
- [ ] File uploaded successfully
- [ ] Homework list showing items
- [ ] Chat with AI responses
- [ ] Console with no errors

---

## Next Steps After Testing

**If all tests pass:**
1. Mark this subtask (subtask-3-4) as "completed"
2. Update implementation_plan.json
3. Commit with message: "auto-claude: subtask-3-4 - End-to-end verification of full homework workflow"
4. Update build-progress.txt with success notes
5. Move to Phase 4 subtasks (polish and error handling)

**If issues are found:**
1. Document all issues in detail
2. Create fix plan
3. Implement fixes
4. Re-run verification
5. Do not mark complete until all issues resolved

---

## Support & Troubleshooting

**Common Issues:**

**Issue:** "No homework items in list after upload"
- Check Network tab for upload response
- Verify MongoDB is running
- Check backend logs for errors

**Issue:** "AI not responding"
- Verify GOOGLE_API_KEY is set in environment
- Check backend logs for Gemini API errors
- Test with simpler question

**Issue:** "Conversation history not persisting"
- Check MongoDB for conversation_history field
- Verify GET /homework/{id} returns history
- Check for localStorage/session issues

**Issue:** "Cannot delete homework"
- Check Network tab for 403/401 errors
- Verify JWT token is valid
- Check MongoDB permissions

---

**End of Manual Testing Guide**
