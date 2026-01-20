# Multi-Signal Struggle Detection - Testing Guide

Complete end-to-end testing guide for the struggle detection and intervention system.

## Overview

The system detects student struggle using three signal categories:
- **Interaction signals (40%)**: Errors, pauses, hints
- **Audio signals (30%)**: Voice hesitation, silence, volume
- **Visual signals (30%)**: Facial emotion, engagement, attention

When struggle is detected, interventions are triggered automatically.

## Prerequisites

1. **MongoDB** running locally or cloud instance
2. **TeachingAssistant service** running on port 8002
3. **Frontend** running on port 5173
4. Active tutoring session (logged in user)

## Quick Start

### 1. Start the Backend

```bash
cd services/TeachingAssistant
python api.py
```

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

### 3. Verify Endpoints

```bash
# Health check
curl http://localhost:8002/health

# Get struggle status (requires auth)
curl -H "Authorization: Bearer <token>" http://localhost:8002/struggle/status
```

## API Endpoints

### POST /signals/update
Receive audio/visual signals from Vision Agents or frontend.

```bash
curl -X POST http://localhost:8002/signals/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_signals": {
      "hesitation_score": 0.8,
      "long_pauses": 3,
      "volume_trend": "decreasing",
      "is_speaking": true
    },
    "visual_signals": {
      "emotion": "frustrated",
      "emotion_struggle_score": 0.9,
      "engagement_score": 0.3,
      "is_distracted": true,
      "face_detected": true
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "session_id": "sess_abc123",
  "struggle_score": 0.72,
  "needs_intervention": true,
  "intervention_triggered": true,
  "intervention_type": "break_suggestion"
}
```

### GET /struggle/status
Get current struggle status for the active session.

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8002/struggle/status
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "struggle_score": 0.45,
  "needs_intervention": true,
  "intervention_urgency": "medium",
  "signal_mode": "multi_signal",
  "signals": {
    "interaction": {
      "long_pause": false,
      "repeated_errors": true,
      "inactivity": false,
      "high_hint_usage": false
    },
    "audio": {
      "hesitation": true,
      "long_pauses": false,
      "decreasing_volume": false,
      "is_speaking": true
    },
    "visual": {
      "frustrated_or_confused": true,
      "disengaged": false,
      "looking_away": false,
      "face_detected": true,
      "emotion": "confused"
    }
  },
  "intervention": {
    "type": "encouragement",
    "message": "You're doing great! Remember, making mistakes is part of learning.",
    "urgency": "medium"
  }
}
```

### POST /struggle/record-error
Record an incorrect answer for struggle tracking.

```bash
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-error
```

### POST /struggle/record-success
Record a correct answer (resets error count).

```bash
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-success
```

### POST /struggle/request-hint
Record a hint request for struggle tracking.

```bash
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/request-hint
```

## Intervention Types

| Type | Trigger Score | Description |
|------|---------------|-------------|
| `hint` | 0.3-0.4 | Long pause - offer guidance |
| `encouragement` | 0.4-0.5 | Early struggle - boost confidence |
| `simplification` | 0.5-0.7 | Repeated errors - break down problem |
| `break_suggestion` | 0.7+ | High struggle - suggest taking a break |

## Frontend Components

### StruggleIndicator
Located at: `frontend/src/components/struggle/StruggleIndicator.tsx`

Visual indicator showing current struggle level:
- **Green** (0-30%): Doing great
- **Yellow** (30-50%): Some challenge
- **Orange** (50-70%): Needs support
- **Red** (70-100%): Struggling (pulsing animation)

### InterventionOverlay
Located at: `frontend/src/components/struggle/InterventionOverlay.tsx`

Overlay displaying intervention messages:
- Auto-shows when intervention triggered
- Dismiss or accept suggestions
- Different styling per intervention type

### Integration Example

```tsx
import { StruggleIndicator, InterventionOverlay } from "@/components/struggle";

function TutoringSession() {
  return (
    <div>
      {/* Add to header */}
      <StruggleIndicator showDetails />

      {/* Add to main content area */}
      <InterventionOverlay
        onAccept={(type) => console.log('Accepted:', type)}
        onDismiss={() => console.log('Dismissed')}
      />
    </div>
  );
}
```

## Testing Scenarios

### Scenario 1: Interaction-Only Mode

Test without audio/visual signals (legacy mode):

1. Start a tutoring session
2. Answer 3 questions incorrectly in a row
3. Verify struggle score increases
4. Verify `simplification` intervention triggers

```bash
# Record 3 errors
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-error
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-error
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-error

# Check status
curl -H "Authorization: Bearer <token>" http://localhost:8002/struggle/status
```

### Scenario 2: Multi-Signal Mode

Test with audio/visual signals:

```bash
# Send frustrated visual + hesitant audio
curl -X POST http://localhost:8002/signals/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_signals": {
      "hesitation_score": 0.7,
      "long_pauses": 2,
      "volume_trend": "decreasing"
    },
    "visual_signals": {
      "emotion": "frustrated",
      "emotion_struggle_score": 0.8,
      "engagement_score": 0.4,
      "is_distracted": false
    }
  }'
```

### Scenario 3: High Struggle (Break Suggestion)

```bash
# Send maximum struggle signals
curl -X POST http://localhost:8002/signals/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_signals": {
      "hesitation_score": 0.95,
      "long_pauses": 5,
      "volume_trend": "decreasing"
    },
    "visual_signals": {
      "emotion": "frustrated",
      "emotion_struggle_score": 0.95,
      "engagement_score": 0.1,
      "is_distracted": true
    }
  }'
```

Expected: `break_suggestion` intervention with HIGH urgency.

### Scenario 4: Recovery (Success Resets Errors)

```bash
# Record errors
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-error
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-error

# Verify errors tracked
curl -H "Authorization: Bearer <token>" http://localhost:8002/struggle/status
# Should show consecutive_errors in signals

# Record success
curl -X POST -H "Authorization: Bearer <token>" http://localhost:8002/struggle/record-success

# Verify reset
curl -H "Authorization: Bearer <token>" http://localhost:8002/struggle/status
# consecutive_errors should be 0
```

## Signal Weights Reference

### Interaction (40%)
| Signal | Weight |
|--------|--------|
| Consecutive errors | 20% |
| Response pauses | 10% |
| Hint requests | 10% |

### Audio (30%)
| Signal | Weight |
|--------|--------|
| Voice hesitation | 15% |
| Long silence | 10% |
| Low volume | 5% |

### Visual (30%)
| Signal | Weight |
|--------|--------|
| Facial emotion | 15% |
| Engagement score | 10% |
| Looking away | 5% |

## Files Modified/Created

### Backend
- `services/TeachingAssistant/api.py` - Added 5 struggle endpoints
- `services/TeachingAssistant/struggle_detector.py` - Signal analysis
- `services/TeachingAssistant/intervention_manager.py` - Intervention logic

### Frontend
- `frontend/src/hooks/query-hooks/useStruggleStatus.ts` - React Query hooks
- `frontend/src/components/struggle/StruggleIndicator.tsx` - Visual indicator
- `frontend/src/components/struggle/InterventionOverlay.tsx` - Intervention display
- `frontend/src/components/struggle/index.ts` - Exports

### Vision Agents (Optional)
- `services/VisionAgents/tutor_agent.py` - Audio/visual processing
- `services/VisionAgents/processors/emotion_processor.py` - Facial detection
- `services/VisionAgents/processors/vad_processor.py` - Voice detection
- `services/VisionAgents/processors/engagement_processor.py` - Attention tracking

## Troubleshooting

### No intervention triggered
1. Check struggle score is above threshold (0.2+)
2. Check cooldown period (2 minutes between interventions)
3. Verify session has correct signals in MongoDB

### Signals not updating
1. Verify JWT token is valid
2. Check session is active
3. Look at TeachingAssistant logs for errors

### Frontend not showing interventions
1. Check `useStruggleStatus` is enabled
2. Verify polling interval (default 10s)
3. Check browser console for API errors

## Integration with Vision Agents

For full audio/visual analysis, run Vision Agents:

```bash
cd services/VisionAgents
pip install vision-agents "vision-agents[getstream, gemini]" fer mediapipe
python tutor_agent.py join --call-id <session-id>
```

Vision Agents automatically sends signals to TeachingAssistant via `teaching_assistant_bridge.py`.

## Contact

For issues with this implementation, check the git history on `v1-multi-signal-struggle-detection` branch.
