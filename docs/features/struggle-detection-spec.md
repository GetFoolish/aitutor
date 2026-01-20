# Spec 013: Proactive Struggle Detection and Intervention

## Overview
Build advanced detection system combining audio, visual, and interaction signals to identify when students are struggling before they give up. Automatically trigger appropriate interventions.

## Priority
**Should** - Core differentiator for proactive tutoring.

## User Stories
1. As a struggling student, I want the AI to help me before I want to quit so that I don't give up on math
2. As a young student, I want the AI to notice when I'm confused so that I don't have to ask for help
3. As a parent, I want the AI to be proactive so that my child has positive learning experiences

## Acceptance Criteria
- [ ] System detects struggle signals: long pauses, repeated errors, inactivity
- [ ] Automatic intervention with appropriate support level
- [ ] Intervention types: hints, encouragement, problem simplification, break suggestion
- [ ] Interventions feel natural and supportive, not robotic
- [ ] Tracking of intervention effectiveness for continuous improvement

## Technical Requirements

### Struggle Detection Signals
1. **Time-based signals**
   - Long pauses (>30s on question)
   - Repeated incorrect attempts (3+)
   - Rapid answer changes (indecision)

2. **Behavioral signals**
   - Scrolling back and forth
   - Hint usage patterns
   - Session abandonment patterns

3. **Multi-modal signals** (from specs 007, 008)
   - Audio frustration indicators
   - Visual confusion signals

### Intervention System
- `InterventionTrigger` - Decides when to intervene
- `InterventionSelector` - Chooses appropriate intervention type
- `InterventionDelivery` - Delivers intervention via voice/UI

### Files to Create
- `services/TeachingAssistant/struggle_detector.py`
- `services/TeachingAssistant/intervention_trigger.py`
- `frontend/src/components/Intervention/InterventionOverlay.tsx`

### Dependencies
- Spec 007 (Audio Analysis)
- Spec 008 (Video Analysis)
- Spec 010 (Encouraging Feedback)
