# 🎨 Gemini Teaches on Scratchpad

**Feature:** AI Tutor draws/writes on scratchpad like a real teacher explaining concepts.

## 🎯 Goal

When explaining a concept, Gemini should be able to:
1. Write text on the scratchpad (like writing on a whiteboard)
2. Draw diagrams (shapes, arrows, graphs)
3. Show step-by-step work (animated/progressive)
4. Sync with voice/text explanation

## 📋 User Story

> "As a student, I want to see the AI tutor draw and write on the scratchpad while explaining a problem, so I can follow along visually like I would with a real teacher."

## 🏗️ Architecture

### Option A: SVG Path Generation (Recommended)

```
[Gemini] → generates drawing instructions (JSON)
    ↓
[Instruction Parser] → converts to tldraw shapes
    ↓
[tldraw Canvas] → renders progressively with animation
    ↓
[Student] → watches explanation unfold
```

### Drawing Instruction Format

```json
{
  "explanation_id": "multiply_7x6",
  "steps": [
    {
      "action": "write",
      "text": "7 × 6 = ?",
      "position": { "x": 100, "y": 50 },
      "style": { "size": "large", "color": "blue" },
      "delay_ms": 0,
      "duration_ms": 1000
    },
    {
      "action": "draw_line",
      "from": { "x": 100, "y": 80 },
      "to": { "x": 200, "y": 80 },
      "delay_ms": 1200
    },
    {
      "action": "write",
      "text": "Let's break it down:",
      "position": { "x": 100, "y": 100 },
      "delay_ms": 1500
    },
    {
      "action": "draw_groups",
      "groups": 7,
      "items_per_group": 6,
      "symbol": "●",
      "position": { "x": 100, "y": 150 },
      "delay_ms": 2000,
      "animate": true
    },
    {
      "action": "write",
      "text": "7 × 6 = 42",
      "position": { "x": 100, "y": 300 },
      "style": { "size": "xlarge", "color": "green" },
      "delay_ms": 5000
    }
  ],
  "total_duration_ms": 6000
}
```

## 🔧 Components Needed

### 1. Gemini Instruction Generator
**File:** `content/scratchpad_generator.py`

```python
def generate_teaching_visuals(question: str, concept: str, grade_level: str) -> dict:
    """
    Uses Gemini to generate scratchpad drawing instructions
    for explaining a concept visually.
    """
    prompt = f"""
    You are a teacher explaining this concept to a {grade_level} student.
    Generate step-by-step visual instructions for drawing on a whiteboard.
    
    Question: {question}
    Concept: {concept}
    
    Return JSON with drawing steps (write, draw_line, draw_shape, etc.)
    Think about: what would you draw to help them understand?
    """
    # Call Gemini, parse response
    return instructions
```

### 2. tldraw Instruction Renderer
**File:** `frontend/src/components/scratchpad/ScratchpadTeacher.tsx`

```typescript
interface TeachingStep {
  action: 'write' | 'draw_line' | 'draw_shape' | 'draw_arrow' | 'highlight';
  // ... params based on action
  delay_ms: number;
  duration_ms?: number;
}

const ScratchpadTeacher: React.FC<{instructions: TeachingStep[]}> = ({instructions}) => {
  const editor = useTldrawEditor();
  
  const playTeaching = async () => {
    for (const step of instructions) {
      await delay(step.delay_ms);
      await executeStep(editor, step);
    }
  };
  
  // Render controls: Play, Pause, Restart, Speed
};
```

### 3. API Endpoint
**File:** `content/api.py`

```python
@app.post("/api/generate/teaching-visual")
async def generate_teaching_visual(request: TeachingVisualRequest):
    """
    Generate scratchpad instructions for teaching a concept.
    """
    instructions = generate_teaching_visuals(
        question=request.question,
        concept=request.concept,
        grade_level=request.grade_level
    )
    return {"instructions": instructions}
```

### 4. Integration with Tutor Flow

When the AI tutor is explaining something:
1. Detect "let me show you" or explanation mode
2. Call `/api/generate/teaching-visual`
3. Open scratchpad panel
4. Play instruction sequence
5. Sync with voice (if using Gemini Live)

## 🎨 Visual Actions Supported

| Action | Description | Example |
|--------|-------------|---------|
| `write` | Add text | "7 × 6 = ?" |
| `draw_line` | Draw a line | Underline, divider |
| `draw_arrow` | Arrow pointing | "This leads to..." |
| `draw_shape` | Rectangle, circle, etc. | Grouping, highlighting |
| `draw_groups` | Visual grouping (for multiplication) | ●●● ●●● ●●● |
| `highlight` | Circle/box existing content | Emphasize answer |
| `erase` | Remove previous content | Clear section |
| `number_line` | Draw a number line | For addition/subtraction |
| `fraction_bar` | Draw fraction visualization | 3/8 of a pizza |
| `graph` | Simple coordinate graph | For algebra |

## 📱 UI/UX Considerations

1. **Controls**
   - Play/Pause button
   - Speed control (0.5x, 1x, 1.5x, 2x)
   - Step forward/backward
   - Restart

2. **Sync with Explanation**
   - Text explanation appears alongside drawing
   - Optional: Voice narration (Gemini Live)

3. **Student Interaction**
   - Can pause and draw their own
   - Can replay specific steps
   - Can ask "show me again"

## 🚀 Implementation Phases

### Phase 1: Basic Text Writing (MVP)
- [ ] Gemini generates text-only instructions
- [ ] tldraw renders text with timing
- [ ] Simple play/pause controls

### Phase 2: Shapes and Diagrams
- [ ] Lines, arrows, rectangles
- [ ] Number lines
- [ ] Fraction visualizations

### Phase 3: Animation Polish
- [ ] Smooth drawing animations
- [ ] Handwriting-style text
- [ ] Erase and redo

### Phase 4: Voice Sync (Gemini Live)
- [ ] Sync with audio explanation
- [ ] Real-time generation during tutoring

## 📊 Success Metrics

- Students understand concepts faster
- Engagement time increases
- "That helped!" feedback
- Replay usage (indicates value)

## 🔗 Related Files

- `frontend/src/components/scratchpad/Scratchpad.tsx` - Current scratchpad (tldraw)
- `content/question_generator.py` - Gemini content generation
- `services/Tutor/` - Tutor service (for integration)

---

**Status:** SPEC COMPLETE - Ready for implementation
**Estimated effort:** 2-3 weeks
**Priority:** To be determined
