# Legacy Tutor Service

`services/Tutor/` is kept only as reference code from the old backend-proxy architecture.

It is not part of the supported runtime:

- `run_tutor.sh` does not start it
- `docker-compose.yml` does not include it
- deploy does not ship it
- frontend uses the direct Gemini Live path in `frontend/src/features/tutor/`

If you need the current tutor integration, start from:

- `frontend/src/features/tutor/tutor-service.ts`
- `services/AuthService/auth_api.py` (`/auth/gemini-token`)
- `services/TeachingAssistant/api.py`
