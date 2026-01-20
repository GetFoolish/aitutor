# Multi-Signal Struggle Detection

Advanced detection system combining audio, visual, and interaction signals to identify when students are struggling before they give up.

## Architecture

```
React Frontend → Stream Video SDK → Stream Edge Network
                                          ↓
                              Vision Agents Backend (Python)
                                    ↓
                        Custom Processors:
                        - EmotionProcessor (facial expressions)
                        - VADProcessor (voice hesitation)
                        - EngagementProcessor (attention tracking)
                                    ↓
                                 Gemini
                                    ↓
                        TeachingAssistant Integration
                                    ↓
                        Struggle Detection + Interventions
```

## Signal Weights

| Category | Signal | Weight |
|----------|--------|--------|
| **Interaction (40%)** | Consecutive errors | 20% |
| | Response pauses | 10% |
| | Hint requests | 10% |
| **Audio (30%)** | Voice hesitation | 15% |
| | Long silence | 10% |
| | Low volume | 5% |
| **Visual (30%)** | Facial emotion | 15% |
| | Engagement score | 10% |
| | Looking away | 5% |

## Intervention Types

| Type | Urgency | Trigger Score | Action |
|------|---------|---------------|--------|
| `hint` | LOW | 0.3-0.5 | Provide subtle guidance |
| `encouragement` | MEDIUM | 0.5-0.6 | Offer positive reinforcement |
| `simplification` | HIGH | 0.6-0.7 | Break down the problem |
| `break_suggestion` | HIGH | 0.7+ | Suggest a short break |

## Files Created

### Vision Agents Backend (`services/VisionAgents/`)

| File | Purpose |
|------|---------|
| `tutor_agent.py` | Main Vision Agent combining all processors with Gemini |
| `teaching_assistant_bridge.py` | HTTP bridge to send signals to TeachingAssistant |
| `processors/emotion_processor.py` | Facial expression detection using FER |
| `processors/vad_processor.py` | Voice Activity Detection for hesitation |
| `processors/engagement_processor.py` | Attention tracking using MediaPipe |
| `.env.example` | Environment configuration template |

### TeachingAssistant (`services/TeachingAssistant/`)

| File | Purpose |
|------|---------|
| `struggle_detector.py` | Multi-signal weighted scoring algorithm |
| `intervention_manager.py` | Intervention type selection and delivery |
| `simulate_signals.py` | Signal simulator for testing |
| `test_multi_signal.py` | Unit tests for multi-signal detection |

## Setup Instructions

### 1. Install Vision Agents Dependencies

```bash
cd services/VisionAgents
pip install vision-agents
pip install "vision-agents[getstream, gemini]"
pip install fer mediapipe opencv-python-headless
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys:
# - STREAM_API_KEY
# - STREAM_API_SECRET
# - GEMINI_API_KEY
```

### 3. Start Services

```bash
# Terminal 1: TeachingAssistant
cd services/TeachingAssistant
python api.py

# Terminal 2: Vision Agents (optional - for full audio/visual)
cd services/VisionAgents
python tutor_agent.py join --call-id test-session

# Terminal 3: Frontend
cd frontend
npm run dev
```

## Testing

### Test Multi-Signal Scoring

```bash
cd services/TeachingAssistant
python test_multi_signal.py
```

### Simulate Struggle Signals

```bash
cd services/TeachingAssistant
python simulate_signals.py
```

Available simulation modes:
- `normal` - Baseline student behavior
- `hesitant` - Frequent pauses and hesitation
- `frustrated` - Negative emotions detected
- `confused` - Confusion signals
- `struggling` - All struggle signals combined

### Manual API Testing

```bash
# Send audio/visual signals
curl -X POST http://localhost:8002/signals/update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "session_id": "test-session",
    "audio_signals": {
      "hesitation_score": 0.8,
      "long_pauses": 3,
      "volume_trend": "decreasing"
    },
    "visual_signals": {
      "emotion": "frustrated",
      "emotion_struggle_score": 0.9,
      "engagement_score": 0.3,
      "is_distracted": true
    }
  }'
```

## Expected Output

When all signals indicate struggle (score > 0.7):

```
[STRUGGLE] Multi-signal score: 0.70
  Interaction: errors=0.60, pauses=0.00, hints=0.20
  Audio: hesitation=0.90, silence=1.00, volume=1.00
  Visual: emotion=0.95 (frustrated), disengage=0.85, away=1.00

INTERVENTION TRIGGERED: break_suggestion (HIGH urgency)
```

## Integration with Gemini

Interventions are delivered to Gemini as system prompts:

```
[SYSTEM INSTRUCTION]
The student appears to be struggling. Please suggest taking a short break
and offer to review the material when they return.
```

Gemini then responds naturally, incorporating the intervention into its teaching approach.

## Future Enhancements

- [ ] Stream Video SDK frontend integration
- [ ] Real-time emotion visualization dashboard
- [ ] Personalized intervention thresholds per student
- [ ] Long-term struggle pattern analysis
- [ ] Parent notification system
