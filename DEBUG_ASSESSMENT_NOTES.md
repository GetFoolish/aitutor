# Dynamic Assessment Debug Instructions

## What this is
This repo now supports a debug banner + console logs for the dynamic assessment flow. Use it to confirm where questions are loaded from (nav state, cache, API) and to verify question counts.

## Files added/updated
- `frontend/.env.example` (new): Vite env template including `VITE_SHOW_DEBUG_BANNER`.
- `DEBUG_ASSESSMENT_NOTES.md` (new): this guide.
- `frontend/src/components/assessment/DynamicAssessment.tsx`: debug banner + console logs + reload logic.
- `frontend/src/components/onboarding/LearnerOnboarding.tsx`: caches assessment payload and guards empty question results.
- `services/DashSystem/dash_api.py`: `GET /api/assessment/dynamic/{assessment_id}` for refresh/resume.
- `content/question_generator.py`: accepts `GOOGLE_API_KEY` as Gemini fallback.
- `run_tutor.sh`: avoids port collision on DASH API startup.
- `README.md`: documents `VITE_SHOW_DEBUG_BANNER`.
- `setup-local-env.sh`: includes `VITE_SHOW_DEBUG_BANNER` template entry.

## Enable the debug banner
1) Set the flag in your frontend env:

```
VITE_SHOW_DEBUG_BANNER=true
```

2) Restart Vite.

## What the banner shows
- assessment id
- question count
- source (nav / cache / api)
- current question index (on question screen)

## Console logs to expect
- `[DynamicAssessment] Using navigation state payload`
- `[DynamicAssessment] Using cached assessment payload`
- `[DynamicAssessment] Reloading assessment from API`
- `[DynamicAssessment] Loaded assessment payload`

## Quick verification checklist
- Start at `/app/onboarding`, complete onboarding, and verify the intro screen shows the right question count.
- Refresh `/app/assessment/dynamic` and verify it reloads from cache/API and renders a question.
- Confirm no blank assessment screen.
