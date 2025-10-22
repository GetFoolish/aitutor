# AI Tutor

AI Tutor is a multimodal teaching assistant that combines several FastAPI services, a real-time media mixer, and a Vite/React frontend that talks to Google’s Gemini Live API. The backend services orchestrate question generation, progress tracking, and classroom tooling, while the frontend surfaces live tutoring sessions.

## Prerequisites
- Python 3.11+ with `venv`
- Node.js 18+ and npm 9+
- Google Gemini API key (for the frontend live console)
- OpenRouter API key (for LLM-assisted helpers such as the question generator)

## Environment Variables
Create a `.env` file in the repository root and add:

```
OPENROUTER_API_KEY=sk-...
GOOGLE_API_KEY=optional-google-rest-key
```

Then create `frontend/.env` for the Vite app:

```
VITE_GEMINI_API_KEY=sk-...
```

The backend loads `.env` automatically via `python-dotenv`. The `GOOGLE_API_KEY` entry is optional today, but keeping it alongside the OpenRouter key makes it easy to expand Gemini usage beyond the frontend later.

## Install Dependencies

```bash
# from the repo root
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

## Run All Services
`run_tutor.sh` activates the virtual environment, starts the three FastAPI services, launches the media mixer, and brings up the Vite dev server:

```bash
./run_tutor.sh
```

The script prints the local URLs and tails logs into the `logs/` directory. Use `Ctrl+C` to stop everything; the script will clean up child processes.

### Individual Components
- **Dash API**: `uvicorn DashSystem.dash_api:app --reload`
- **SherlockED Exam API**: `uvicorn SherlockEDApi.app.main:app --reload --port 8001`
- **Media Mixer**: `python MediaMixer/media_mixer.py`
- **Frontend (manual)**:
  ```bash
  cd frontend
  npm run dev
  ```

## Configuration Notes
- `config.json` controls which LLM models OpenRouter calls for each use case.
- Teaching assistant documentation and the Gemini integration plan live under `TeachingAssistant/`. The Python Gemini client is not yet implemented; the current Gemini usage is confined to the React Live API console.

## Verification Checklist
- `pip list` shows the dependencies from `requirements.txt`.
- `npm run build` inside `frontend/` succeeds.
- Visiting the frontend URL (default `http://localhost:3001`) prompts for media permissions and connects to Gemini if the API key is valid.
