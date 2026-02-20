# AI Tutor Bug Fix Battle Plan
## Stage 1: Plan (APPROVAL REQUIRED)

**Created:** 2026-02-20
**Status:** AWAITING USER APPROVAL
**Estimated Effort:** 3-5 focused sessions (8-12 hours total)

---

## Executive Summary

This plan systematically addresses 6 critical bug categories identified in the AI Tutor codebase:

1. **Silent Failures** (49 files, est. 100+ instances) — Highest Impact
2. **ThreadPoolExecutor Timeout Bug** (9 locations) — Blocks assessment reliability
3. **Assessment Flow Breaks** (6 documented failure modes) — User-facing critical
4. **Frontend Layout Fragility** (CSS specificity war) — UX degradation
5. **MongoDB Schema Validation** (0 validation, nested dict access) — Data integrity
6. **Test Coverage Gap** (1 test file for 89 Python files) — Regression risk

**Priority Order:** 1 → 2 → 3 → 4 → 5 → 6 (impact × urgency)

---

## Issue Categorization & Impact Analysis

### Priority 1: Silent Exception Swallowing
**Files Affected:** 49 Python files
**Pattern:** `except Exception: pass` or `return None` without logging
**Current Impact:**
- Question generation fails silently → downstream explosions
- Assessment dead-ends appear random (no error context)
- Debugging requires psychic powers

**Root Cause Examples:**
```python
# content_v1.py:152
except Exception:
    return None  # ← No log, no trace, just... nothing

# dash_api.py:683
except Exception:
    pass  # ← Error vanishes into the void
```

**Fix Strategy:**
- Add structured logging with context (student_id, skill_id, operation)
- Replace bare `except Exception` with specific exception types
- Return explicit error types (`Result[T, Error]` pattern) instead of `None`
- Add Sentry/error tracking integration points

**Affected Critical Paths:**
- Question generation pipeline (content_v1.py)
- Assessment startup (dash_api.py lines 1143, 2094)
- JIT question fallback (ai_question_provider.py:652)

---

### Priority 2: ThreadPoolExecutor Context Manager Bug
**Files Affected:** 9 locations across 6 files
**Pattern:** `with ThreadPoolExecutor(...) as executor:` + `future.result(timeout=T)`
**Current Impact:**
- "Fast" timeouts still block 60-76 seconds (documented in AGENTS.md line 76)
- Assessment startup feels broken even when working
- Users abandon assessments during "Creating personalized questions..."

**Root Cause:**
```python
# dash_api.py:2094
with ThreadPoolExecutor(max_workers=5) as executor:
    pending = {executor.submit(...) for ...}
    # ... timeout logic here ...

# ← BUG: Context manager waits for ALL workers on __exit__
# even if you already timed out the futures!
```

**Fix Strategy:**
- Remove `with` context manager (manually manage executor lifecycle)
- Call `executor.shutdown(wait=False, cancel_futures=True)` on timeout
- Add wall-clock timing proof in tests (must measure actual latency, not just function return)

**Files to Fix:**
1. `dash_api.py` lines 1143, 2094, 2923, 2983 (4 instances)
2. `content_v1.py` lines 1055, 1093, 1400, 1444, 1600 (5 instances)
3. `ai_question_provider.py` line 611
4. `content_generation_service.py` lines 380, 568
5. `curriculum_generator.py` lines 337, 412, 512

**Validation:**
- Add test: `test_executor_timeout_actually_fast()` measuring wall-clock time
- Acceptance: Assessment startup < 25s end-to-end (current: 60-76s)

---

### Priority 3: Assessment Flow Reliability
**Documented Bugs from AGENTS.md:**
1. Assessments return 1-2 questions instead of 10 (line 10)
2. Cross-subject contamination (science gets math, line 12)
3. Adaptive breaks at Q4-Q5 with 503 errors (line 20)
4. Dead-end "Still preparing..." infinite retry (line 24)
5. Radio grading mismatch (`selectedChoiceIds` format, line 17)
6. Duplicate questions generated (line 7)

**Root Causes:**
- **1-2 questions:** JIT generation timeout + no fallback pool
- **Cross-subject:** Global `dash_system` state contamination
- **Q4-Q5 break:** Pool exhaustion + slow refill (ThreadPoolExecutor bug)
- **Infinite retry:** No circuit breaker on repeated 503s
- **Radio grading:** Frontend sends `choice-<index>`, backend expects `choice_<uuid>`
- **Duplicates:** Content hash dedup not enforced in all code paths

**Fix Strategy:**
1. **Question count guarantee:** Pre-warm pool before starting assessment
2. **Subject isolation:** Add subject validation to question pop operations
3. **Circuit breaker:** Max 3 retries on 503, then show hard error UI
4. **Radio grading:** Normalize choice IDs on backend to handle both formats
5. **Dedup enforcement:** Add unique constraint on content_hash, catch DuplicateKeyError

**Files to Modify:**
- `dash_api.py` (assessment startup, next-question endpoint)
- `content_generation_service.py` (pool pre-warming)
- `dash_system.py` (subject validation on pop)
- Frontend: `AssessmentFlow.tsx` (circuit breaker UI)
- Frontend: `RendererComponent.tsx` (choice ID normalization)

**Validation:**
- Test: `test_assessment_completes_10_questions()` (no skip, no retry)
- Test: `test_subject_isolation()` (math assessment never gets science questions)
- Test: `test_circuit_breaker()` (3 failed 503s → error UI, not infinite spinner)

---

### Priority 4: Frontend Layout Fragility
**Current State:** CSS specificity war zone
**Symptoms from AGENTS.md:**
- Submit buttons below fold (line 21)
- Questions require scrolling (line 22, 29)
- Panels clip/overlap (lines 25, 26, 34)
- Dropdown detaches from anchor (line 38)

**Root Causes in App.scss:**
```scss
.streaming-console {
  height: calc(100dvh - 48px);  // ← Fixed height
  overflow-y: hidden;           // ← No scroll allowed
}

.question-panel {
  height: 100%;                 // ← Inherits fixed height
  overflow-y: hidden;           // ← No scroll allowed
}

// ← Problem: Long questions have nowhere to go!
```

**Fix Strategy:**
1. **Container hierarchy audit:** Map all height/overflow declarations
2. **Viewport-fit algorithm:** Questions scale to fit viewport, not overflow
3. **Action button persistence:** Submit/Next always visible (sticky footer or viewport guarantee)
4. **Remove conflicting declarations:** Only ONE container should control overflow

**Files to Modify:**
- `frontend/src/App.scss` (container hierarchy)
- `frontend/src/components/assessment/*.tsx` (question scaling)
- `frontend/src/components/renderer/*.tsx` (widget rendering)

**Validation:**
- Manual test at 1366×768 (AGENTS.md line 110 baseline)
- Automated: Playwright screenshot test → measure button visibility
- Gate: Zero browser scroll in assessment view

---

### Priority 5: MongoDB Schema Validation
**Current State:** Zero validation, nested dict access with `.get()` chains
**Risk Examples:**
```python
# Fragile nested access (content_v1.py pattern)
(first_doc.get("item") or {}).get("question") or {}).get("content")
# ← If shape is slightly off, returns None → cascading failures
```

**Collections at Risk:**
- `content_pool` (Perseus JSON structure)
- `ai_generated_questions` (item format)
- `assessment_sessions` (state tracking)
- `student_misconceptions` (analytics)

**Fix Strategy:**
1. **Add Pydantic models** for critical collections
2. **Validation on read:** Parse documents into models, fail fast with clear errors
3. **Migration script:** Validate existing data, flag/fix malformed docs

**Files to Create:**
- `services/DashSystem/models/question_schemas.py` (Pydantic models)
- `services/shared/mongo_validated.py` (wrapper with auto-validation)

**Files to Modify:**
- `content_v1.py` (use validated models)
- `content_generation_service.py` (validate on insert)

**Validation:**
- Test: `test_malformed_question_rejected()` (insert invalid → raises ValidationError)
- Test: `test_missing_field_explicit_error()` (readable error, not None cascade)

---

### Priority 6: Test Coverage Expansion
**Current State:** 1 integration test file (`test_dash.py`) for 89 Python files
**Coverage:** Unknown (pytest.ini configured for 50%, but not enforced)

**Critical Missing Tests:**
- Question generation pipeline (content_v1.py — 2068 lines, 0 tests)
- Assessment flow (dash_api.py — 4489 lines, 1 basic test)
- ThreadPoolExecutor timeout validation (0 tests measuring wall-clock time)
- Schema validation (0 tests for malformed data)

**Fix Strategy:**
1. **Baseline coverage report:** Run `pytest --cov` to measure current state
2. **Add critical path tests:**
   - `test_question_generation_pipeline.py` (JIT, pool, fallback)
   - `test_assessment_flow.py` (startup, next, completion)
   - `test_executor_timeout.py` (wall-clock timing validation)
3. **Target:** 60% coverage on critical services (DashSystem, ContentV1)

**Files to Create:**
- `services/DashSystem/test_question_generation.py`
- `services/DashSystem/test_assessment_reliability.py`
- `services/DashSystem/test_executor_performance.py`

**Validation:**
- CI gate: Coverage must not decrease
- Target: 60% coverage on `services/DashSystem/` directory

---

## Implementation Order & Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation (Sessions 1-2)                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Fix Silent Failures (Priority 1)                         │
│    ├─ Add logging infrastructure                            │
│    ├─ Replace bare except blocks                            │
│    └─ Add error type returns                                │
│                                                              │
│ 2. Fix ThreadPoolExecutor Bug (Priority 2)                  │
│    ├─ Remove context managers                               │
│    ├─ Add manual shutdown                                   │
│    └─ Add wall-clock timing tests                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: User-Facing Fixes (Session 3)                      │
├─────────────────────────────────────────────────────────────┤
│ 3. Fix Assessment Flow (Priority 3)                         │
│    ├─ Pool pre-warming                                      │
│    ├─ Subject isolation                                     │
│    ├─ Circuit breaker UI                                    │
│    └─ Radio grading fix                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: UX & Stability (Session 4)                         │
├─────────────────────────────────────────────────────────────┤
│ 4. Fix Frontend Layout (Priority 4)                         │
│    ├─ Container hierarchy audit                             │
│    ├─ Viewport-fit algorithm                                │
│    └─ Action button persistence                             │
│                                                              │
│ 5. Add Schema Validation (Priority 5)                       │
│    ├─ Pydantic models                                       │
│    ├─ Validation wrapper                                    │
│    └─ Migration script                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Verification (Session 5)                           │
├─────────────────────────────────────────────────────────────┤
│ 6. Expand Test Coverage (Priority 6)                        │
│    ├─ Baseline coverage report                              │
│    ├─ Critical path tests                                   │
│    └─ CI coverage gate                                      │
└─────────────────────────────────────────────────────────────┘
```

**Dependencies:**
- Phase 2 depends on Phase 1 (silent failures fixed = easier debugging)
- Phase 3 can run in parallel after Phase 2
- Phase 4 validates all previous phases

---

## Success Criteria (Definition of Done)

### Phase 1 Complete When:
- ✅ Zero bare `except Exception: pass` in critical paths (content_v1, dash_api, ai_question_provider)
- ✅ All errors logged with context (student_id, skill_id, operation)
- ✅ ThreadPoolExecutor timeout < 5s wall-clock time (down from 60-76s)
- ✅ Test: `test_executor_timeout_actually_fast()` passes

### Phase 2 Complete When:
- ✅ Assessment completes 10 questions reliably (no 503 dead-ends)
- ✅ Subject isolation enforced (test: math never gets science questions)
- ✅ Circuit breaker UI shows after 3 failed retries
- ✅ Radio grading works for both `choice-<index>` and `choice_<uuid>` formats

### Phase 3 Complete When:
- ✅ Submit/Next buttons always visible at 1366×768 viewport
- ✅ Zero browser scroll in assessment view (AGENTS.md gate #110)
- ✅ Dropdown widgets stay anchored (no detached options)
- ✅ Pydantic models validate all question reads/writes
- ✅ Malformed data raises explicit ValidationError (not silent None)

### Phase 4 Complete When:
- ✅ Coverage ≥60% on `services/DashSystem/` directory
- ✅ Tests prove: question generation, assessment flow, timeout behavior
- ✅ CI gate fails on coverage decrease

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Breaking existing working flows** | High | Critical | Add tests BEFORE refactoring; feature flags for risky changes |
| **ThreadPoolExecutor fix causes new hangs** | Medium | High | Wall-clock timing tests; manual executor lifecycle |
| **Schema validation breaks existing data** | Medium | High | Migration script validates before enforcing; gradual rollout |
| **Frontend layout changes break mobile** | Medium | Medium | Responsive testing at 768px, 1366px, 1920px breakpoints |
| **Test suite adds too much CI time** | Low | Low | Parallelize tests; focus on critical paths only |

---

## Open Questions for User

1. **Silent failures:** Should we add Sentry/error tracking, or just structured logging?
2. **ThreadPoolExecutor:** Can we test the timeout fix in isolation, or does it need full assessment integration?
3. **Assessment pre-warming:** How many questions should we pre-generate per subject? (Current: 0, Proposed: 15)
4. **Frontend layout:** Should we enforce zero-scroll as a hard gate, or allow graceful overflow for extreme edge cases?
5. **Test coverage:** Is 60% a reasonable target, or should we aim higher for critical services?
6. **Migration order:** Should we fix everything in one PR, or break into smaller incremental PRs per phase?

---

## Next Steps

**IF APPROVED:**
1. User confirms success criteria match expectations
2. User answers open questions
3. Proceed to **Stage 2: Work** (start with Priority 1 - Silent Failures)

**IF CHANGES NEEDED:**
1. User provides feedback on plan
2. Revise plan based on feedback
3. Re-submit for approval

---

**Awaiting your approval to proceed. Any changes needed?**
