# Error Handling Verification Guide

## Overview
This document describes how to manually verify the error handling improvements for file uploads and API failures in the Homework Upload feature.

## Test Scenarios

### 1. File Size Limit (> 10MB)
**Test:** Upload a file larger than 10MB

**Steps:**
1. Open the Homework panel in FloatingControlPanel
2. Go to the Upload tab
3. Try to upload a file larger than 10MB (create one with: `dd if=/dev/zero of=large_file.pdf bs=1024 count=11000`)

**Expected Error:**
```
Error
File size exceeds server limit. Please upload a file smaller than 10MB.
```

**Visual:** Red error box with border-[3px], shadow, error icon (X), and dismiss button

---

### 2. Unsupported File Type
**Test:** Upload a file with unsupported extension

**Steps:**
1. Open the Homework panel
2. Go to the Upload tab
3. Try to upload a file with unsupported type (e.g., .zip, .exe, .mp4)

**Expected Error:**
```
Error
Unsupported file type. Please upload PDF, JPG, PNG, DOCX, or TXT files.
```

**Note:** This error appears immediately after file selection (client-side validation)

---

### 3. Network Failure During Upload
**Test:** Simulate network disconnection during upload

**Steps:**
1. Open the Homework panel
2. Select a valid file (e.g., a PDF under 10MB)
3. Click "Upload Homework"
4. Quickly disconnect network (turn off WiFi or use browser DevTools Network throttling → Offline)

**Expected Error:**
```
Error
Network error. Please check your internet connection and try again.
```

**Alternative Test:**
- Use browser DevTools → Network → Set to "Offline" before clicking upload
- Or use browser extension to simulate network errors

---

### 4. Backend Service Down
**Test:** Upload file when HomeworkAssistant service is not running

**Steps:**
1. Stop the HomeworkAssistant backend service (port 8004)
   ```bash
   # Find and kill the process
   lsof -ti:8004 | xargs kill -9
   ```
2. Open the Homework panel
3. Select a valid file
4. Click "Upload Homework"

**Expected Error:**
```
Error
Network error. Please check your internet connection and try again.
```

**Note:** When service is completely down, it appears as a network error (connection refused)

**Alternative:** If service returns 503 status:
```
Error
Service temporarily unavailable. Please try again in a few moments.
```

---

### 5. Server Error (5xx Status)
**Test:** Backend returns 500 Internal Server Error

**Steps:**
1. This requires modifying backend to return 500 error, or use a proxy to inject errors
2. Alternative: Test with other API methods (listHomework, getHomework, etc.) by stopping MongoDB

**Expected Error:**
```
Error
Server error occurred. Please try again later.
```

---

### 6. Authentication Error
**Test:** Upload without valid JWT token

**Steps:**
1. Clear localStorage to remove JWT token
   ```javascript
   localStorage.clear()
   ```
2. Or in DevTools: Application → Local Storage → Clear All
3. Try to upload a file

**Expected Error:**
```
Error
Authentication required. Please sign in and try again.
```

---

## Error Display Features

### Visual Design
- **Border:** 3px solid red (destructive color)
- **Background:** Semi-transparent red (destructive/10)
- **Shadow:** 2px shadow in destructive color
- **Layout:** Flex container with icon, content, and dismiss button

### Error Structure
```
[X Icon] Error
         [Detailed error message]
                                  [X Dismiss]
```

### Dismiss Functionality
- Click the X button on the right to dismiss the error
- Error is also cleared when starting a new upload
- Error persists until user dismisses or retries

---

## Testing Checklist

- [ ] File > 10MB shows size limit error
- [ ] Unsupported file type shows format error (immediate, client-side)
- [ ] Network disconnection shows network error
- [ ] Backend service down shows appropriate error
- [ ] Server errors (5xx) show server error message
- [ ] Authentication errors show auth error message
- [ ] Error box has proper neo-brutalist styling
- [ ] Error icon (X) is visible
- [ ] Error can be dismissed
- [ ] Error clears on new upload attempt
- [ ] Error messages are user-friendly and actionable
- [ ] No console.log statements in production code

---

## Error Handling Coverage

### homework-service.ts
All API methods now include comprehensive error handling:
- `uploadHomework()` - 413, 415, 401/403, 503, 5xx, network errors
- `listHomework()` - 401/403, 503, 5xx, network errors
- `getHomework()` - 404, 401/403, 503, 5xx, network errors
- `askQuestion()` - 404, 401/403, 503, 5xx, network errors
- `deleteHomework()` - 404, 401/403, 503, 5xx, network errors
- `getFileBlob()` - 404, 401/403, 503, 5xx, network errors

### HomeworkUpload.tsx
- Client-side file validation (size, type)
- Error state management
- Enhanced error display UI
- Error dismissal
- Error clearing on retry

---

## Notes

1. **Network vs Service Errors:** When backend is completely down (connection refused), it appears as a network error. Service unavailable (503) requires backend to be running but overloaded.

2. **Client-side Validation:** File size and type validation happens immediately on file selection, before upload button is clicked.

3. **Server-side Validation:** Backend may also validate file size/type, which would trigger different error messages from the server.

4. **Error Persistence:** Errors remain visible until user dismisses them or starts a new upload, ensuring users have time to read and understand the error.

5. **Accessibility:** Error messages use semantic HTML and ARIA labels for screen readers.
