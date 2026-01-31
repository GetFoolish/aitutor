# Feedback Loop History

This file tracks issues found during feedback loop iterations.
Claude reviewer loads this before each review to watch for recurring issues.

---

## 2026-01-31 (Initial Setup)

### Known Issues to Watch For:
- Radio widgets without choices (empty `options.choices` array)
- Questions with no widgets defined
- Numeric input widgets without answers
- "No answer choices available" error in UI
- Connection refused errors when backend not running
- Port mismatches between frontend .env and running services

### Validation Layers Added:
1. **Backend** (`content/question_generator.py`): `_validate_question_structure()` method
2. **Frontend** (`RendererComponent.tsx`): `validatePerseusItem()` function
3. **E2E Tests** (`e2e/dynamic-assessment.spec.ts`): Critical error checks

### Design System Rules (Neo-Brutalism):
- Spacing: 8pt grid (8, 16, 24, 32, 48, 64px)
- Borders: 3px solid #000
- Shadows: 4px 4px 0 #000 (solid offset, no blur)
- Border radius: 8px, 12px, or 999px (pills)
- Primary color: #6C63FF
- Background: #FFFDF5

### Recurring Issue Patterns:
(To be updated as issues are found and fixed)

---

## Issue Template

When adding new issues, use this format:

```
## YYYY-MM-DD

### Issues Found:
- [severity] Description (file:line)

### Root Cause:
Brief explanation

### Fix Applied:
What was changed

### Status: FIXED | RECURRING | OPEN
```
