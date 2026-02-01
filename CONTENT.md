# 📚 Content Generation Feature

AI-powered question generation with Innocent Drinks tone of voice.

## Quick Start

```bash
# 1. Start the content API
cd content
source ../.venv/bin/activate
python -m content.api

# 2. Start the frontend
cd frontend
npm install
npm run dev

# 3. Open the dynamic assessment
open http://localhost:3000/app/assessment/dynamic
```

## What's Included

### Backend (`content/`)
- `api.py` - FastAPI endpoints for question generation
- `question_generator.py` - LLM-based question generation
- `tone_guidelines.py` - Innocent Drinks style guidelines
- `dynamic_assessment.py` - Assessment flow logic
- `example_retriever.py` - MongoDB question retrieval
- `memory_personalizer.py` - Personalization with user memories

### Frontend
- `DynamicAssessment.tsx` - Assessment UI component
- `assessment-questions.css` - Styling
- Route: `/app/assessment/dynamic`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/generate/question` | POST | Generate single question |
| `/api/generate/assessment` | POST | Generate assessment set |
| `/api/topics` | GET | List available topics |
| `/api/skills` | GET | List available skills |

## Generate a Question

```bash
curl -X POST "http://localhost:8001/api/generate/question" \
  -H "Content-Type: application/json" \
  -d '{"skill": "fractions", "grade_level": "3-5"}'
```

## Tone Examples

The system generates questions in Innocent Drinks style:

**Math:**
> "imagine you're sharing a pizza with your friends. the pizza's cut into 8 slices..."

**Science:**
> "so, your lovely little houseplant, let's call her fernando, is photosynthesising away..."

**Reading:**
> "alright, picture this: you're baking cookies (yum!)..."

## Environment Variables

```bash
GOOGLE_API_KEY=your_gemini_key  # For LLM generation
MONGODB_URI=mongodb://localhost:27017  # Optional: for example retrieval
```

## Testing

```bash
# Test the API
curl http://localhost:8001/health

# Generate a test question
curl -X POST http://localhost:8001/api/generate/question \
  -H "Content-Type: application/json" \
  -d '{"skill": "multiplication", "grade_level": "3-5"}'
```
