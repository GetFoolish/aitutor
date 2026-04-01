# 🐛 Bug Tracking - AI Tutor
**Last Updated:** 2026-02-26
**Status:** 15 bugs found, 0 fixed

---

## 🔴 CRITICAL (4) - MUST FIX IMMEDIATELY

### Bug #1: Empty Answer Submission Race Condition ⏱️
**File:** `frontend/src/components/assessment/AssessmentQuestion.tsx`
**Line:** 616-648

**Problem:**
```typescript
if (!rendererRef.current) {
  console.error('[AssessmentQuestion] rendererRef is null');
  setEmptyWarning(true);
  setTimeout(() => setEmptyWarning(false), 2000);
  return; // ❌ Does not prevent double-submit!
}
```

**Fix:**
```typescript
const handleSubmit = () => {
  if (isAnswered || isSubmitting) return;

  setIsSubmitting(true); // ✅ Set BEFORE any checks

  if (!rendererRef.current) {
    console.error('[AssessmentQuestion] rendererRef is null');
    setEmptyWarning(true);
    setTimeout(() => setEmptyWarning(false), 2000);
    setIsSubmitting(false); // ✅ Reset on error
    return;
  }
  // ... rest of logic
}
```

**Test:**
```bash
# Rapid-click test
1. Load question
2. Spam-click "Submit Answer" button 10x in <1 second
3. Should only submit once
```

---

### Bug #13: No Exit Confirmation ⚠️
**File:** `frontend/src/components/assessment/AssessmentFlow.tsx`
**Line:** 52, 77

**Problem:**
```typescript
// State is defined...
const [showExitDialog, setShowExitDialog] = useState(false);
const unblockRef = useRef<(() => void) | null>(null);

// ...but NEVER rendered in JSX!
// User can lose all progress by hitting back button
```

**Fix:**
```tsx
// Add to component return:
{showExitDialog && (
  <div className="exit-dialog-overlay">
    <div className="exit-dialog">
      <h2>Exit Assessment?</h2>
      <p>Your progress will be lost. Are you sure?</p>
      <button onClick={() => {
        setShowExitDialog(false);
        history.goBack();
      }}>
        Yes, Exit
      </button>
      <button onClick={() => setShowExitDialog(false)}>
        Cancel
      </button>
    </div>
  </div>
)}

// Add useEffect for browser back button:
useEffect(() => {
  const unblock = history.block((location, action) => {
    if (action === 'POP' && !completed) {
      setShowExitDialog(true);
      return false; // Block navigation
    }
    return true;
  });
  unblockRef.current = unblock;
  return () => unblock();
}, [completed]);
```

**Test:**
```bash
1. Start assessment
2. Answer 3 questions
3. Hit browser back button
4. Should see confirmation dialog
5. Click "Yes, Exit" → should navigate away
6. Click "Cancel" → should stay on assessment
```

---

### Bug #5: Silent Network Errors 🔇
**File:** `frontend/src/components/auth/DevLogin.tsx`
**Line:** 76-83

**Problem:**
```typescript
fetch(`${DASH_API_URL}/api/start-subject`, {
  method: 'POST',
  headers: {...},
  body: JSON.stringify({ subject: selectedSubject, region: 'US' })
}).catch(() => {}); // ❌ SILENTLY SWALLOWS ALL ERRORS
```

**Fix:**
```typescript
import { toast } from "@/components/ui/sonner";

fetch(`${DASH_API_URL}/api/start-subject`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${data.token}`
  },
  body: JSON.stringify({ subject: selectedSubject, region: 'US' })
}).catch((err) => {
  console.error('Subject switch failed:', err);
  toast.error('Backend connection failed', {
    description: 'Assessment may not load correctly. Please refresh the page.',
    duration: 5000
  });
});
```

**Test:**
```bash
1. Stop DASH API: kill $(lsof -ti:8000)
2. Try to log in via dev-login
3. Should see error toast
4. Start DASH API again
5. Login should show success
```

---

### Bug #11: Missing Accessibility Labels ♿
**File:** `frontend/src/components/auth/DevLogin.tsx`
**Line:** 197-222, 308-343

**Problem:**
```tsx
{/* Name input - NO LABEL */}
<input
  type="text"
  value={name}
  placeholder="Student name (optional)"
/>

{/* Custom subject - NO LABEL */}
<input
  type="text"
  value={customSubject}
  placeholder="e.g. Geography, Music Theory..."
/>
```

**Fix:**
```tsx
{/* Name input */}
<label htmlFor="student-name" className="sr-only">
  Student name (optional)
</label>
<input
  id="student-name"
  type="text"
  value={name}
  placeholder="Student name (optional)"
  aria-label="Student name (optional)"
/>

{/* Custom subject */}
<label htmlFor="custom-subject" className="sr-only">
  Custom subject name
</label>
<input
  id="custom-subject"
  type="text"
  value={customSubject}
  placeholder="e.g. Geography, Music Theory..."
  aria-label="Enter a custom subject name"
/>
```

**Test:**
```bash
1. Install screen reader (macOS: VoiceOver, Windows: NVDA)
2. Navigate to dev-login
3. Tab to name input → should announce "Student name (optional)"
4. Tab to custom subject → should announce "Enter a custom subject name"
```

---

## 🟠 HIGH PRIORITY (5) - FIX THIS WEEK

### Bug #2: No Loading Phase Feedback
**File:** `AssessmentFlow.tsx:47`
**Status:** State exists, not rendered

**Quick Fix:**
```tsx
{loading && (
  <div className="loading-indicator">
    {loadPhase === 'fast' && '⏳ Loading question...'}
    {loadPhase === 'generating' && '🤖 AI is generating your question...'}
    {loadPhase === 'slow' && '⚠️ Taking longer than usual, please wait...'}
  </div>
)}
```

---

### Bug #3: Memory Leak in Abort Controllers
**File:** `AssessmentFlow.tsx:71-73`

**Fix:**
```typescript
useEffect(() => {
  return () => {
    // Cleanup on unmount
    if (abortRef.current) {
      abortRef.current.abort();
    }
    timersRef.current.forEach(timer => clearTimeout(timer));
    if (submitOverlayTimerRef.current) {
      clearTimeout(submitOverlayTimerRef.current);
    }
  };
}, []);
```

---

### Bug #6: Missing Estimated Grade
**File:** `App.tsx:177`

**Fix:**
```typescript
const data = await response.json();

// Show results with fallback
const gradeDisplay = data.estimated_grade
  ? `Grade Level: ${data.estimated_grade}`
  : 'Grade level will be calculated and emailed to you';

alert(`Assessment Complete!\nScore: ${data.score}/${data.total}\n${gradeDisplay}`);
```

---

### Bug #8: Perseus Pre-Selection Workaround Fragile
**File:** `AssessmentQuestion.tsx:222-262`

**Better Fix (MutationObserver):**
```typescript
useEffect(() => {
  const container = document.getElementById('question-content-container');
  if (!container) return;

  container.classList.add('no-pre-selection');

  // Watch for Perseus DOM changes
  const observer = new MutationObserver(() => {
    const pressedBtns = container.querySelectorAll('button[aria-pressed="true"]');
    pressedBtns.forEach(btn => btn.setAttribute('aria-pressed', 'false'));
  });

  observer.observe(container, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['aria-pressed']
  });

  const handleFirstClick = () => {
    container.classList.remove('no-pre-selection');
    observer.disconnect();
  };

  container.addEventListener('click', handleFirstClick, { once: true });

  return () => {
    observer.disconnect();
    container.removeEventListener('click', handleFirstClick);
  };
}, [question, questionNumber]);
```

---

### Bug #9: Floating Panel Z-Index Risk
**File:** `App.tsx` + `FloatingControlPanel`

**Test Plan:**
```bash
1. Open assessment on 800px height viewport
2. Find question with dropdown widget
3. Click dropdown → should expand above floating panel
4. If obscured, add z-index to dropdown container
```

---

## 🟡 MEDIUM PRIORITY (4) - FIX THIS SPRINT

### Bug #4: Custom Subject Validation No Feedback
**File:** `DevLogin.tsx:308-326`

**Fix:**
```tsx
const [validationError, setValidationError] = useState('');

// In onChange:
if (trimmed.length > 0 && trimmed.length < 2) {
  setValidationError('Subject must be at least 2 characters');
} else if (trimmed.length >= 2 && !hasLetter) {
  setValidationError('Subject must contain at least one letter');
} else {
  setValidationError('');
}

// Render error:
{validationError && (
  <div className="error-text">{validationError}</div>
)}
```

---

### Bug #7: Scratchpad Capture Performance
**File:** `App.tsx:261-263`

**Fix:**
```typescript
import { throttle } from 'lodash';

const throttledFrameCapture = useMemo(
  () => throttle((canvas) => {
    mediaMixer.updateScratchpadFrame(canvas);
  }, 500), // Only capture every 500ms
  [mediaMixer]
);

<ScratchpadCapture onFrameCaptured={throttledFrameCapture}>
```

---

### Bug #12: Console Warning Suppression Too Broad
**File:** `index.tsx:35`

**Fix:**
```typescript
const SUPPRESSED = [
  'findDOMNode is deprecated',
  'A component is changing an uncontrolled',
  '@khanacademy/perseus', // Only suppress Perseus warnings
];
```

---

### Bug #14: Mobile Button Crush
**File:** `DevLogin.tsx:241-279`

**Fix:**
```tsx
style={{
  padding: ultraNarrow ? '10px 16px' : '14px 24px',
  fontSize: ultraNarrow ? '14px' : '16px'
}}
```

---

## 🟢 LOW PRIORITY (2) - BACKLOG

### Bug #10: Progress Display Ambiguity
**File:** `AssessmentQuestion.tsx:762`

**Fix:**
```typescript
// Add comment
const effectiveQuestionNumber = isAnswered
  ? questionNumber + 1  // questionNumber is 1-based (1,2,3...)
  : questionNumber;
```

---

### Bug #15: Fingerprint Memory Usage
**File:** `AssessmentFlow.tsx:94-98`

**Fix:**
```typescript
// Simple djb2 hash
function hashString(str: string): string {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 33) ^ str.charCodeAt(i);
  }
  return hash.toString(36);
}

const contentFingerprint = useCallback((q: Question): string => {
  const content = q?.question?.content || '';
  const widgets = JSON.stringify(q?.question?.widgets || {});
  return hashString(content + '|' + widgets);
}, []);
```

---

## 📊 Progress Tracker

| Priority | Total | Fixed | Remaining |
|----------|-------|-------|-----------|
| 🔴 Critical | 4 | 0 | 4 |
| 🟠 High | 5 | 0 | 5 |
| 🟡 Medium | 4 | 0 | 4 |
| 🟢 Low | 2 | 0 | 2 |
| **TOTAL** | **15** | **0** | **15** |

---

## 🧪 Testing Checklist

After fixing bugs, run these tests:

### Manual Tests
- [ ] Empty answer spam-click (Bug #1)
- [ ] Browser back button during assessment (Bug #13)
- [ ] Backend offline error toast (Bug #5)
- [ ] Screen reader on all form inputs (Bug #11)
- [ ] Slow question generation feedback (Bug #2)
- [ ] Mobile layout on 375px width (Bug #14)
- [ ] Dropdown over floating panel (Bug #9)

### Automated Tests (TODO)
- [ ] E2E: Complete assessment flow
- [ ] E2E: Network error scenarios
- [ ] Unit: All scoring-utils functions
- [ ] A11y: axe-core audit
- [ ] Performance: Memory leak check

---

## 📝 Developer Notes

**Before Starting:**
1. Read `QA_BUG_REPORT.md` for full context
2. Create feature branch: `git checkout -b fix/qa-critical-bugs`
3. Fix bugs in order: Critical → High → Medium → Low

**After Fixing Each Bug:**
1. Update this file: change `[ ]` to `[x]` in Progress Tracker
2. Add test case to automated suite
3. Run manual test from checklist above
4. Commit with message: `fix: Bug #X - [short description]`

**Before Merging:**
1. All 4 critical bugs must be fixed
2. All manual tests passing
3. No new console errors
4. QA approval required

---

**Questions?** See `QA_BUG_REPORT.md` for detailed reproduction steps and code snippets.
