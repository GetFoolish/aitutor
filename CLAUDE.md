# Teachr.Live — Claude Code Rules

## The Cardinal Rule

**Fix code. Do not write about code.**

When given a bug: fix it, run the build, commit. No markdown files. No QA reports. No analysis docs. No new .md files of any kind. If you find yourself writing a report instead of fixing code — STOP. Fix the code.

## Ship Gate

Before saying "done" on ANY task, you must pass ALL of these:

```bash
cd frontend && npm run build          # Must pass with 0 errors
cd frontend && npm run lint           # Must pass
cd .. && python3 -m pytest tests/ -x  # Must pass
```

If any of these fail, fix them before reporting done. Never say "done" when the build is broken.

## Verification Protocol (Stolen from Verification Specialist Pattern)

After every fix, give a verdict:
- PASS — build green, feature works end-to-end, visually correct
- PARTIAL — build green but edge case still broken (describe exactly what)
- FAIL — build broken or regression introduced

Never report PASS unless you've actually run the build and it passed.

## Design System — Non-Negotiable

Every UI element must follow these rules EXACTLY. No exceptions.

```css
/* Borders */
border: 2px solid #000000;
border-radius: 0px;

/* Shadows */
box-shadow: 4px 4px 0px #000000;

/* Primary color */
--primary: #FF4B4B;

/* Background */
--bg: #FFFDF5;

/* Typography scale */
H1: 32px bold uppercase letter-spacing:0.1em
H2: 12px bold uppercase letter-spacing:0.15em color:#666
Body: 16px regular
Caption: 13px color:#666
Button: 14px bold uppercase

/* Spacing — 8px grid ONLY */
/* All margins/paddings must be: 8, 16, 24, 32, 40, 48px */
```

## Critical API Rules

### `get_next_question_flexible()` — Only Valid Parameters

```python
def get_next_question_flexible(
    self,
    student_id: str,
    current_time: float,
    exclude_question_ids: Optional[List[str]] = None,
    force_grade_range: bool = False,
    user_profile: Optional['UserProfile'] = None,
    exclude_skill_ids: Optional[List[str]] = None,
    fast_mode: bool = False
) -> Optional[Question]:
```

DO NOT pass: `difficulty`, `grade`, `subject`, `used_skill_ids` — these do not exist.

### Three-Layer API Rule

When changing any endpoint, check ALL THREE layers:
1. Backend function signature in `services/DashSystem/dash_system.py`
2. FastAPI endpoint in `services/DashSystem/dash_api.py`
3. Frontend fetch in `frontend/src/` components

All three must agree on parameter names and types.

## Assessment Flow — Must Work End-to-End

The assessment must pass this full flow before any task is "done":
1. /app/dev-login → select subject → select age → START ASSESSMENT button turns active
2. Question loads within 10 seconds
3. Select answer → Submit → correct/incorrect feedback shows
4. Next question loads
5. Complete 10 questions → results screen shows
6. Exit button → confirmation dialog → navigates home cleanly

Never close a task until this entire flow works.

## What "Done" Means

Done = build passes + lint passes + tests pass + full assessment flow works + no console errors.

NOT done = "I made the changes" or "it should work now" without running verification.

## Banned Actions

- Creating .md files (QA reports, bug reports, analysis docs, anything)
- Saying "done" without running the build
- Adding TODO comments instead of fixing things
- Partial fixes ("I fixed the main issue, the edge case can be addressed later")
- Writing console.log debug statements and leaving them in

## Commit Message Format

```
fix: <what was broken> — <what you did>
polish: <what you improved>
feat: <what you added>
```

One commit per logical change. Always include what was verified.

## File Size Rule (from Phantom)

Files over 300 lines must be split. If approaching 250 lines, plan the split.

## Toolbar Overlap

FloatingControlPanel is on the right side. Main content must always have:
```css
padding-right: 72px; /* accounts for toolbar width */
```
Test on viewports ≤ 920px height.

## Perseus Widget Fields

When modifying Perseus questions, ALL required fields must be present:
- `content`, `widgets`, `images` in question
- `type`, `options` in each widget
- Never remove fields, only add them
