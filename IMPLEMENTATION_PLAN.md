# Implementation Plan: Fix All 16 User Testing Issues

**Date:** 2026-02-20
**Scope:** Comprehensive fixes for P0 → P1 → P2 issues from user testing report
**Estimated Total Time:** 20-25 hours

---

## P0 - CRITICAL ISSUES (Must fix first)

### Issue #1: Empty Answer Accepted as CORRECT
**Severity:** P0 - Data Integrity
**Impact:** Assessment scores are meaningless
**Files:**
- `frontend/src/lib/scoring-utils.ts` (lines 418-419, 259-270)
- `frontend/src/components/assessment/AssessmentQuestion.tsx` (line 285-296)

**Root Cause:**
- Dropdown widget validation accepts `value: 0` or default index as valid selection
- `hasUserInput()` doesn't validate dropdown index is within choices array
- Perseus may be initializing with default value instead of null

**Fix Strategy:**
1. **scoring-utils.ts line 418** - Add stricter validation:
   ```typescript
   } else if (widgetDef.type === 'dropdown') {
       const choices = widgetDef.options?.choices || [];
       const idx = (widgetInput as any)?.value ?? (widgetInput as any)?.selected;
       // NEW: Validate idx is a valid choice index AND not placeholder
       if (idx != null && idx >= 0 && idx < choices.length) {
           // Ensure it's not the placeholder "Select one..." option
           const selectedChoice = choices[idx];
           if (selectedChoice && selectedChoice.content) return true;
       }
       return false;
   ```

2. **scoring-utils.ts line 259** - Add defensive check:
   ```typescript
   } else if (widgetDef.type === 'dropdown') {
       const choices = widgetDef.options?.choices || [];
       const selectedIdx = (widgetInput as any)?.value ?? (widgetInput as any)?.selected;
       if (selectedIdx != null && selectedIdx >= 0 && selectedIdx < choices.length) {
           const selectedChoice = choices[selectedIdx];
           // NEW: Reject if no content (placeholder option)
           if (selectedChoice?.content && selectedChoice.content.trim() !== "Select one...") {
               widgetCorrect = !!selectedChoice.correct;
           }
       }
   ```

3. **Backend validation** - Add server-side check in `dash_api.py`:
   - Find answer submission endpoint (likely `/api/submit-answer` or similar)
   - Add validation: reject submissions with null/undefined/invalid widget inputs
   - Return 400 Bad Request if dropdown has no valid selection

**Testing:**
- [ ] Load dropdown question
- [ ] Click Submit without selecting answer
- [ ] Verify: "PLEASE ANSWER BEFORE SUBMITTING" message appears
- [ ] Verify: Backend rejects submission with 400 error
- [ ] Select valid answer → Submit → Verify correct scoring

**Estimate:** 2 hours

---

### Issue #2: Science 404 on Next Question
**Severity:** P0 - Core Feature Broken
**Impact:** Science assessments fail after Q1
**Files:**
- `services/DashSystem/dash_api.py` (lines 2602-2650)
- `frontend/src/components/assessment/AssessmentFlow.tsx` (line 303)

**Root Cause:**
- Session document not persisted properly for AI-generated subjects
- Session lookup fails: `find_one({"assessment_id": ..., "status": "in_progress"})` returns None
- Science curriculum generation may not complete before assessment starts

**Fix Strategy:**
1. **dash_api.py line 2615** - Add defensive logging:
   ```python
   session = mongo_db.db["assessment_sessions"].find_one({
       "assessment_id": payload.assessment_id,
       "user_id": user_id,
       "status": "in_progress"
   })
   if not session:
       # NEW: Log details for debugging
       all_sessions = list(mongo_db.db["assessment_sessions"].find({"user_id": user_id}))
       logger.error(f"Session not found for assessment_id={payload.assessment_id}, user_id={user_id}")
       logger.error(f"All user sessions: {all_sessions}")
       raise HTTPException(status_code=404, detail="Assessment session not found")
   ```

2. **Session creation verification** - Check `/assessment/start-adaptive/{subject}`:
   - Ensure session document is created BEFORE returning first question
   - Add `created_at`, `updated_at` timestamps
   - Set `status: "in_progress"` explicitly
   - Wait for curriculum generation to complete before marking ready

3. **Session status update** - In `/assessment/next` endpoint:
   - Update `session.updated_at` on every question fetch
   - Track `questions_asked` array to prevent duplicates
   - Add retry logic: if session not found, attempt to recreate from context

4. **Frontend error handling** - AssessmentFlow.tsx line 303:
   ```typescript
   const response = await apiUtils.post('/assessment/next', { assessment_id: assessmentId });
   if (!response.ok) {
       // NEW: Better error context
       const error = await response.json();
       console.error('Assessment next failed:', {
           assessment_id: assessmentId,
           subject,
           error
       });
       // Attempt session recovery
       if (response.status === 404) {
           // Try to restart from checkpoint
           const recovery = await apiUtils.post('/assessment/recover', {
               assessment_id: assessmentId,
               current_question: currentQuestion
           });
           if (recovery.ok) return recovery.json();
       }
       throw new Error(`HTTP ${response.status}: ${error.detail}`);
   }
   ```

**Testing:**
- [ ] Start Science assessment from dev-login
- [ ] Answer Q1 correctly
- [ ] Click "Next Question"
- [ ] Verify: Q2 loads without 404 error
- [ ] Answer Q2-Q5 to confirm session persistence
- [ ] Check MongoDB: `assessment_sessions` collection has valid document

**Estimate:** 4 hours

---

### Issue #3: Exit Flow Broken
**Severity:** P0 - User Experience
**Impact:** Can't cleanly exit assessment
**Files:**
- `frontend/src/components/assessment/AssessmentFlow.tsx` (lines 641-658)
- `frontend/src/index.tsx` (lines 295-298)
- `frontend/src/components/auth/AssessmentGuard.tsx` (lines 95-112)

**Root Cause:**
- Exit button navigates to `/app?subject=X`
- AssessmentGuard interprets this as new assessment start request
- No proper landing page for post-assessment state

**Fix Strategy:**
1. **Create assessment completion/exit page**:
   - New component: `AssessmentComplete.tsx`
   - Shows: score summary, skills practiced, time spent
   - Actions: "Review Answers", "Try Another Subject", "Back to Dashboard"

2. **Update exit handler** - AssessmentFlow.tsx line 658:
   ```typescript
   const handleExit = () => {
       // Clear assessment state
       if (unblockRef.current) {
           unblockRef.current();
           unblockRef.current = null;
       }
       setAssessmentId(null);
       sessionStorage.removeItem('assessmentSubject');

       // NEW: Navigate to proper exit page
       const exitRoute = assessmentId
           ? `/app/assessment-exit?assessment_id=${assessmentId}&subject=${subject}`
           : `/app/dashboard`;
       history.replace(exitRoute);
   };
   ```

3. **Add route** - index.tsx:
   ```tsx
   <Route path="/app/assessment-exit" element={<AssessmentExit />} />
   <Route path="/app/dashboard" element={<Dashboard />} />
   ```

4. **AssessmentGuard fix** - Prevent auto-restart:
   ```typescript
   useEffect(() => {
       const urlSubject = urlParams.get('subject');
       const fromExit = urlParams.get('fromExit');

       // NEW: Don't auto-start if coming from exit
       if (urlSubject && !fromExit && urlSubject !== savedSubject) {
           ensureSubjectReady(urlSubject);
       }
   }, [urlParams]);
   ```

**Testing:**
- [ ] Start Biology assessment
- [ ] Answer Q1
- [ ] Click ✕ EXIT
- [ ] Verify: Navigate to exit page (NOT auto-restart)
- [ ] Verify: Exit page shows assessment summary
- [ ] Click "Try Another Subject" → Navigate to subject selector
- [ ] Click "Back to Dashboard" → Navigate to dashboard

**Estimate:** 3 hours

---

## P1 - HIGH PRIORITY (Significant UX Problems)

### Issue #4: No Exit Confirmation
**Severity:** P1
**Impact:** Accidental exits lose progress
**Files:**
- `frontend/src/components/assessment/AssessmentFlow.tsx` (lines 641-689)

**Fix Strategy:**
1. **Add confirmation dialog component**:
   ```tsx
   const [showExitDialog, setShowExitDialog] = useState(false);

   const handleExitClick = (e: React.MouseEvent) => {
       e.stopPropagation();
       setShowExitDialog(true);
   };

   const confirmExit = () => {
       setShowExitDialog(false);
       // Existing exit logic...
   };
   ```

2. **Dialog UI** (neo-brutalism styled):
   ```tsx
   {showExitDialog && (
       <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
           <div className="bg-white border-[4px] border-black shadow-[8px_8px_0_0_#000] p-8 max-w-md">
               <h3 className="text-2xl font-bold mb-4">Exit Assessment?</h3>
               <p className="mb-6">Your progress will be lost. Are you sure?</p>
               <div className="flex gap-4">
                   <button onClick={confirmExit} className="...red-button...">
                       Yes, Exit
                   </button>
                   <button onClick={() => setShowExitDialog(false)} className="...gray-button...">
                       Cancel
                   </button>
               </div>
           </div>
       </div>
   )}
   ```

**Testing:**
- [ ] Start assessment
- [ ] Click EXIT
- [ ] Verify: Confirmation dialog appears
- [ ] Click "Cancel" → Dialog closes, stay in assessment
- [ ] Click EXIT again → Click "Yes, Exit" → Navigate away

**Estimate:** 1 hour

---

### Issue #5: Session Not Recovered on Refresh
**Severity:** P1
**Impact:** F5 refresh loses all progress
**Files:**
- `frontend/src/components/assessment/AssessmentFlow.tsx` (lines 34, 219-220)
- `services/DashSystem/dash_api.py` (new endpoint needed)

**Fix Strategy:**
1. **Save session to localStorage** - AssessmentFlow.tsx line 232:
   ```typescript
   const assessmentData = await response.json();
   setAssessmentId(assessmentData.assessment_id);
   setCurrentQuestion(assessmentData.question);

   // NEW: Persist session
   localStorage.setItem('active_assessment', JSON.stringify({
       assessment_id: assessmentData.assessment_id,
       subject,
       started_at: Date.now(),
       question_count: 1
   }));
   ```

2. **Recovery on mount** - Add useEffect:
   ```typescript
   useEffect(() => {
       const savedSession = localStorage.getItem('active_assessment');
       if (savedSession && !assessmentId) {
           const session = JSON.parse(savedSession);
           // Check if session is recent (< 1 hour old)
           if (Date.now() - session.started_at < 3600000) {
               resumeAssessment(session.assessment_id);
           } else {
               localStorage.removeItem('active_assessment');
           }
       }
   }, []);

   const resumeAssessment = async (id: string) => {
       try {
           const response = await apiUtils.get(`/assessment/resume/${id}`);
           const data = await response.json();
           setAssessmentId(id);
           setCurrentQuestion(data.current_question);
           setSubject(data.subject);
       } catch (error) {
           console.error('Failed to resume:', error);
           localStorage.removeItem('active_assessment');
       }
   };
   ```

3. **Backend resume endpoint** - dash_api.py:
   ```python
   @router.get("/assessment/resume/{assessment_id}")
   async def resume_assessment(
       assessment_id: str,
       user_id: str = Depends(get_current_user)
   ):
       session = mongo_db.db["assessment_sessions"].find_one({
           "assessment_id": assessment_id,
           "user_id": user_id,
           "status": "in_progress"
       })
       if not session:
           raise HTTPException(404, "Session expired or not found")

       # Return current state
       return {
           "assessment_id": assessment_id,
           "subject": session["subject"],
           "current_question": session.get("last_question"),
           "questions_answered": len(session.get("questions_asked", [])),
           "total_questions": session.get("total_questions", 10)
       }
   ```

**Testing:**
- [ ] Start assessment
- [ ] Answer Q1-Q3
- [ ] Press F5 (page refresh)
- [ ] Verify: Assessment resumes at Q3 (not Q1)
- [ ] Check localStorage: `active_assessment` exists
- [ ] Complete assessment → Verify localStorage cleared

**Estimate:** 3 hours

---

### Issue #6: First Option Auto-Selected
**Severity:** P1
**Impact:** Biases students toward option A
**Files:**
- `frontend/src/lib/general-utils.ts` (lines 25-65)
- `frontend/src/components/assessment/AssessmentQuestion.tsx` (lines 285-296)

**Fix Strategy:**
1. **Fix choice initialization** - general-utils.ts line 35:
   ```typescript
   const getChoiceStates = ({ choices, isStatic, showSolutions, choiceStates }):
     // Case 1: Review mode — select correct answers
     if (isStatic || showSolutions === "all") {
       return choices.map((choice) => ({
         ...defaultState,
         selected: !!choice.correct,
       }));
     }

     // NEW: Case 2: Assessment mode — NEVER pre-select
     if (showSolutions === "none" || !showSolutions) {
       return choices.map(() => ({
         ...defaultState,
         selected: false,  // Explicit false
         checked: false,
         crossedOut: false,
         highlighted: false
       }));
     }

     // Case 3: Initial state
     return choices.map(() => ({...defaultState}));
   ```

2. **Clear AI-generated selection state** - AssessmentQuestion.tsx line 290:
   ```tsx
   q.question.widgets[key] = {
     ...w,
     options: {
       ...w.options,
       choices: sanitizeChoicesArray(w.options.choices).map(choice => ({
         ...choice,
         // NEW: Force clear any pre-selection from AI
         selected: undefined,
         checked: undefined,
         crossedOut: false
       })),
       selectedChoiceIds: undefined,
       deselectEnabled: false,
     },
   };
   ```

3. **Add backend validation** - Verify AI question generation doesn't set `selected: true`:
   - Check `ai_question_provider.py` or similar
   - Ensure generated questions have `selected: false` or undefined

**Testing:**
- [ ] Load 10 different questions
- [ ] Verify: NO options pre-selected on load
- [ ] Select option B → Submit → Verify scoring works
- [ ] Load next question → Verify previous selection doesn't carry over

**Estimate:** 2 hours

---

### Issue #7: Keyboard Navigation Broken
**Severity:** P1 - Accessibility
**Impact:** Keyboard users can't submit answers
**Files:**
- `frontend/src/components/assessment/AssessmentQuestion.tsx` (lines 708-749)
- `frontend/src/index.css` (lines 10-34)

**Fix Strategy:**
1. **Add tabindex management** - AssessmentQuestion.tsx:
   ```tsx
   {/* Hint button */}
   <button
     tabIndex={0}  // NEW: Explicit tab order
     className="..."
     onClick={handleRevealHint}
   >
     HINT
   </button>

   {/* Submit button */}
   <button
     tabIndex={0}  // NEW: Explicit tab order
     disabled={!keScore || keScore.empty}
     className="..."
     onClick={handleSubmit}
   >
     SUBMIT
   </button>
   ```

2. **Update focus styling** - index.css:
   ```css
   /* Neo-brutalism focus indicators */
   *:focus-visible {
     outline: 4px solid #000 !important;  /* BLACK, not blue */
     outline-offset: 0px;
     box-shadow: 0 0 0 8px rgba(0, 0, 0, 0.1);
   }

   .dark *:focus-visible {
     outline-color: #fff !important;
     box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.1);
   }

   /* Buttons get extra highlight */
   button:focus-visible {
     transform: translate(1px, 1px);
     box-shadow: 3px 3px 0 #000 !important;
   }
   ```

3. **Test tab order**:
   - Question text (not focusable)
   - Option A
   - Option B
   - Option C
   - Option D
   - HINT button
   - SUBMIT button
   - EXIT button (top right)

**Testing:**
- [ ] Load question
- [ ] Press Tab repeatedly
- [ ] Verify: Focus moves A → B → C → D → HINT → SUBMIT → EXIT
- [ ] Verify: Focus indicators are BLACK (not blue)
- [ ] Press Enter on selected option → Verify selection
- [ ] Tab to SUBMIT → Press Enter → Verify submission

**Estimate:** 2 hours

---

### Issue #8: Slow AI Subject Loading (15-25s)
**Severity:** P1 - Performance
**Impact:** Users abandon during loading
**Files:**
- `services/DashSystem/dash_api.py` (lines 2341-2600)
- `services/DashSystem/content_v1.py` (image generation)

**Root Cause:**
- JIT generation takes 8-15s per question
- Image generation adds 3-5s (20% of questions)
- Validation loops retry up to 3x

**Fix Strategy:**
1. **Reduce IMAGE_PROBABILITY** - .env:
   ```
   IMAGE_PROBABILITY=0.10  # Was 0.20
   ```

2. **Pre-warm pool for popular subjects** - Add startup task:
   ```python
   # In dash_api.py startup
   @router.on_event("startup")
   async def warmup_popular_subjects():
       popular = ["Math", "Science", "English", "Biology"]
       for subject in popular:
           for grade in range(5, 9):  # Focus on middle grades
               asyncio.create_task(
                   content_service.ensure_pool(
                       skill_id=f"{subject}_Grade{grade}_Sample",
                       difficulty_bucket="medium",
                       count=5
                   )
               )
   ```

3. **Improve cache hit rate** - dash_api.py line 2450:
   - Increase warm-start cache from 3 skills to 10 skills
   - Cache by subject+grade, not just individual skills

4. **Add progress indicator** - AssessmentFlow.tsx:
   ```tsx
   {isStarting && (
       <div className="...">
           <div className="mb-4">
               <div className="text-sm mb-2">
                   {phase === 'warmup' && 'Checking question bank...'}
                   {phase === 'generation' && 'Creating your first question...'}
                   {phase === 'validation' && 'Quality check...'}
               </div>
               <div className="w-full bg-gray-200 h-2 border-2 border-black">
                   <div
                       className="bg-blue-500 h-full transition-all"
                       style={{ width: `${progress}%` }}
                   />
               </div>
           </div>
           <p className="text-sm">This may take 10-20 seconds for new subjects</p>
       </div>
   )}
   ```

**Testing:**
- [ ] Clear all pools: `db.content_pool.deleteMany({})`
- [ ] Start English assessment
- [ ] Measure time to first question (target: <10s)
- [ ] Verify: Progress bar updates through phases
- [ ] Start second English assessment
- [ ] Verify: Loads faster (<3s) due to cache

**Estimate:** 4 hours

---

## P2 - MEDIUM PRIORITY (Polish/UX)

### Issue #9: No Visual Correct/Wrong Distinction
**Severity:** P2
**Impact:** Students don't see which answer was right
**Files:**
- `frontend/src/components/question-display/mcq-fix.css` (new rules needed)
- `frontend/src/components/assessment/AssessmentQuestion.tsx` (line 564)

**Fix Strategy:**
1. **Add data attributes after scoring** - AssessmentQuestion.tsx:
   ```typescript
   const handleSubmit = async () => {
       // Existing scoring...
       const result = scorePerseusQuestion(currentQuestion, userAnswerState);
       setKeScore(result);
       setShowFeedback(true);

       // NEW: Mark choices as correct/incorrect
       const choiceElements = document.querySelectorAll('.choice');
       choiceElements.forEach((el, idx) => {
           const choice = currentQuestion.question.widgets['radio1'].options.choices[idx];
           if (choice?.correct) {
               el.setAttribute('data-feedback', 'correct');
           } else if (userAnswerState.widgets['radio1']?.selected === idx) {
               el.setAttribute('data-feedback', 'incorrect');
           }
       });
   };
   ```

2. **Add CSS rules** - mcq-fix.css:
   ```css
   /* Post-answer feedback */
   .choice[data-feedback="correct"] {
       background-color: #4ADE80 !important;  /* Green */
       border-color: #000 !important;
       border-width: 5px !important;
       box-shadow: 4px 4px 0 #000 !important;
   }

   .choice[data-feedback="incorrect"] {
       background-color: #FF6B6B !important;  /* Red */
       border-color: #000 !important;
       border-width: 5px !important;
       box-shadow: 4px 4px 0 #000 !important;
       opacity: 0.7;
   }

   .choice[data-feedback] {
       pointer-events: none;  /* Disable clicks after answer */
   }

   /* Dark mode */
   .dark .choice[data-feedback="correct"] {
       background-color: #22C55E !important;
   }
   .dark .choice[data-feedback="incorrect"] {
       background-color: #EF4444 !important;
   }
   ```

**Testing:**
- [ ] Answer question CORRECTLY
- [ ] Verify: Correct choice turns GREEN
- [ ] Verify: Other choices remain default
- [ ] Answer question INCORRECTLY
- [ ] Verify: Selected choice turns RED
- [ ] Verify: Correct choice turns GREEN
- [ ] Verify: Can't click choices after submission

**Estimate:** 1.5 hours

---

### Issue #10: Subtle Selection Feedback
**Status:** FALSE POSITIVE - Design is correct
**No action needed** - Current bright yellow selection is intentional neo-brutalism design

---

### Issues #11-13: Design Mismatches
**Severity:** P2
**Impact:** Inconsistent design language
**Files:**
- `frontend/src/components/floating-control-panel/FloatingControlPanel.tsx` (line 862)

**Fix:**
1. **Remove rounding** - FloatingControlPanel.tsx line 862:
   ```tsx
   className={cn(
     "...",
     "border-[4px] rounded-none",  // Was: rounded-lg md:rounded-xl
     "shadow-[4px_4px_0_0_#000]",
     "..."
   )}
   ```

**Testing:**
- [ ] Open FloatingControlPanel
- [ ] Verify: Sharp corners (no rounding)
- [ ] Verify: 4px black border + 4px hard shadow

**Estimate:** 15 minutes

---

### Issue #14: Duplicate Questions
**Status:** Known issue (content hash tracking)
**Defer to separate fix** - This requires backend content service changes

---

### Issue #15: Invisible Focus Indicators
**Severity:** P2 - Accessibility
**Impact:** Keyboard users can't see focus
**Files:**
- `frontend/src/index.css` (lines 10-18)

**Fix:**
Already covered in Issue #7 (keyboard navigation) - same CSS changes

**Estimate:** Included in #7

---

### Issue #16: Dark Mode Contrast
**Severity:** P3
**Impact:** Minor visual inconsistency
**Files:**
- `frontend/src/components/floating-control-panel/FloatingControlPanel.tsx`

**Fix:**
1. **Unify dark backgrounds** - FloatingControlPanel.tsx:
   ```tsx
   className={cn(
     "...",
     "bg-white dark:bg-neutral-800",  // Was: dark:bg-[#000000]
     "..."
   )}
   ```

**Testing:**
- [ ] Toggle dark mode
- [ ] Verify: Panel background matches card backgrounds (consistent gray)

**Estimate:** 10 minutes

---

## IMPLEMENTATION ORDER

### Phase 1: P0 Critical (Must fix first)
1. Issue #1: Empty answer validation (2h)
2. Issue #3: Exit flow broken (3h)
3. Issue #2: Science 404 (4h)
**Total: 9 hours**

### Phase 2: P1 High Priority
4. Issue #4: Exit confirmation (1h)
5. Issue #7: Keyboard navigation (2h)
6. Issue #6: Auto-selected option (2h)
7. Issue #5: Session recovery (3h)
8. Issue #8: Slow loading (4h)
**Total: 12 hours**

### Phase 3: P2 Polish
9. Issue #9: Visual feedback (1.5h)
10. Issues #11-13: Design fixes (0.25h)
11. Issue #15: Focus indicators (included in #7)
12. Issue #16: Dark mode (0.15h)
**Total: 2 hours**

### Skipped
- Issue #10: False positive (no fix needed)
- Issue #14: Deferred to content service refactor

---

## TESTING CHECKLIST

After all fixes:
- [ ] Load Biology assessment (AI-generated)
- [ ] Complete full 10-question flow without errors
- [ ] Press F5 mid-assessment → Verify recovery
- [ ] Click EXIT → Confirm dialog → Cancel → Stay in assessment
- [ ] Click EXIT → Confirm → Verify clean exit
- [ ] Test keyboard-only flow (Tab + Enter)
- [ ] Toggle dark mode → Verify all styling
- [ ] Load Science → Verify no 404 on next question
- [ ] Submit empty dropdown → Verify rejection
- [ ] Verify correct/incorrect visual feedback
- [ ] Load 5 questions → Verify no duplicates
- [ ] Measure load time for new subject (<15s target)

---

## RISKS & DEPENDENCIES

1. **Backend session changes** - Requires MongoDB updates, test on staging first
2. **Perseus widget behavior** - May have unexpected side effects on question rendering
3. **Performance regression** - Image generation changes could affect quality
4. **Dark mode edge cases** - Need comprehensive testing across all components

---

## SUCCESS CRITERIA

✅ **P0 Fixed:**
- No empty answers score as correct
- Science assessments complete without 404
- Clean exit flow to dashboard/summary page

✅ **P1 Fixed:**
- Exit confirmation prevents accidental loss
- Session recovery works on F5 refresh
- Keyboard navigation reaches all controls
- Loading <15s for AI subjects

✅ **P2 Fixed:**
- Correct/incorrect answers visually distinguished
- Design system consistent (4px borders, no rounding)
- Focus indicators visible and neo-brutalist

✅ **Overall:**
- All 16 issues addressed or deferred with rationale
- No regressions in existing functionality
- User testing feedback incorporated
