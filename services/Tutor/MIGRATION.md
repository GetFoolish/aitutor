# Legacy Migration Note

This document is preserved only as historical context for the retired backend Tutor proxy.

The active architecture is now:

- frontend tutor client in `frontend/src/features/tutor/`
- ephemeral Gemini token issuance in `services/AuthService/auth_api.py`
- backend session orchestration in `services/TeachingAssistant/api.py`

Do not use this folder as the source of truth for bootstrap, compose, or deployment.
