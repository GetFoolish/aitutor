# Scratchpad & AI Drawing Feature

This document explains how to set up and use the scratchpad feature, which allows both students and the AI tutor to draw on a shared whiteboard.

## Overview

The scratchpad is a digital whiteboard that:
- Students can use to work through problems visually
- AI tutor can draw on to provide visual explanations
- Captures frames to send to Gemini for multimodal understanding

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      App.tsx                            │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ ScratchpadCapture│  │      Scratchpad            │  │
│  │ (Frame capture)  │  │  (react-sketch-canvas)     │  │
│  └─────────────────┘  └─────────────────────────────┘  │
│                              ▲                          │
│                              │                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │           TutorDrawingHandler                    │   │
│  │  (Registers draw_on_scratchpad tool with Gemini)│   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Scratchpad (`src/components/scratchpad/Scratchpad.tsx`)

The main whiteboard component using `react-sketch-canvas`.

**Features:**
- Color picker (6 colors: black, red, green, blue, orange, purple)
- Stroke width selector (2px, 4px, 8px, 12px)
- Eraser tool
- Undo/Redo
- Clear board (with confirmation dialog)

**Global Reference:**
```typescript
window.__sketchCanvasRef  // ReactSketchCanvasRef for AI drawing
```

### 2. TutorDrawingHandler (`src/components/tutor-drawing-handler/TutorDrawingHandler.tsx`)

Registers the `draw_on_scratchpad` function with Gemini Live API.

**Tool Schema:**
```typescript
{
  name: "draw_on_scratchpad",
  parameters: {
    strokesJson: string,  // JSON array of strokes
    clearFirst: boolean   // Clear canvas before drawing
  }
}
```

**Stroke Format:**
```json
[
  {
    "points": [{"x": 100, "y": 100}, {"x": 200, "y": 200}],
    "strokeColor": "#ff0000",
    "strokeWidth": 4
  }
]
```

### 3. ScratchpadCapture (`src/components/scratchpad-capture/ScratchpadCapture.tsx`)

Captures frames of the question content and scratchpad drawings to send to Gemini.

**Features:**
- Captures every 5 seconds (throttled)
- Composites question content with scratchpad overlay
- Skips capture if canvas not ready or empty

## Installation

### 1. Install Dependencies

```bash
cd frontend
npm install react-sketch-canvas
```

### 2. Verify Files Exist

Ensure these files are in place:
- `src/components/scratchpad/Scratchpad.tsx`
- `src/components/scratchpad-capture/ScratchpadCapture.tsx`
- `src/components/tutor-drawing-handler/TutorDrawingHandler.tsx`

### 3. Update System Prompt

The AI tutor's system prompt (`public/ai_tutor_system_prompt.md`) should include the drawing capability section:

```markdown
### 7. Drawing on the Scratchpad (Visual Teaching Tool)
- **Capability:** You have access to the `draw_on_scratchpad` tool...
```

## Usage

### For Students

1. Click the paint/brush icon to open the scratchpad
2. Select a color and stroke width
3. Draw on the canvas
4. Use eraser to remove strokes
5. Use undo/redo as needed
6. Click "Clear Board" to start fresh

### For AI Tutor

The AI tutor can draw by calling the `draw_on_scratchpad` tool:

```javascript
// Example: Draw a horizontal line
{
  "strokesJson": "[{\"points\":[{\"x\":50,\"y\":300},{\"x\":750,\"y\":300}],\"strokeColor\":\"#1e1e1e\",\"strokeWidth\":4}]",
  "clearFirst": false
}
```

**Common Shapes:**

1. **Horizontal Line:**
```json
[{"points":[{"x":100,"y":200},{"x":700,"y":200}],"strokeColor":"#1e1e1e","strokeWidth":4}]
```

2. **Circle (approximated):**
```json
[{"points":[{"x":400,"y":200},{"x":450,"y":210},{"x":480,"y":250},{"x":490,"y":300},{"x":480,"y":350},{"x":450,"y":390},{"x":400,"y":400},{"x":350,"y":390},{"x":320,"y":350},{"x":310,"y":300},{"x":320,"y":250},{"x":350,"y":210},{"x":400,"y":200}],"strokeColor":"#e03131","strokeWidth":4}]
```

3. **Arrow pointing right:**
```json
[
  {"points":[{"x":100,"y":300},{"x":600,"y":300}],"strokeColor":"#1971c2","strokeWidth":4},
  {"points":[{"x":550,"y":250},{"x":600,"y":300},{"x":550,"y":350}],"strokeColor":"#1971c2","strokeWidth":4}
]
```

## Troubleshooting

### Scratchpad not appearing
- Ensure `isScratchpadOpen` state is being toggled correctly
- Check that `.scratchpad-container` CSS is applied

### AI tutor not drawing
1. Check console for `✅ TutorDrawingHandler: Registered draw_on_scratchpad tool`
2. Verify scratchpad is open before asking AI to draw
3. Check for tool call errors in console

### "Export function called before canvas loaded" error
- This is handled gracefully - the capture will retry
- If persistent, check that `sketchCanvasRef` is being set correctly

### Gemini connection closing with "Internal error"
- May be due to tool schema issues
- Try simplifying the strokesJson content
- Check Gemini API quotas/limits

## API Reference

### ReactSketchCanvasRef Methods

```typescript
interface ReactSketchCanvasRef {
  clearCanvas(): void;
  undo(): void;
  redo(): void;
  eraseMode(enabled: boolean): void;
  exportImage(type: 'png' | 'jpeg'): Promise<string>;
  exportPaths(): Promise<CanvasPath[]>;
  loadPaths(paths: CanvasPath[]): void;
}
```

### CanvasPath Format

```typescript
interface CanvasPath {
  drawMode: boolean;
  strokeColor: string;
  strokeWidth: number;
  paths: Array<{ x: number; y: number }>;
}
```

## Configuration

### Canvas Dimensions
- Default canvas: Fills container (typically ~800x600)
- Coordinate system: X (0-800), Y (0-600) recommended

### Capture Settings
- Capture interval: 5000ms (5 seconds)
- Output size: 1280x720 composite
- Scratchpad overlay: 640x360 in bottom-right corner

### Colors Available
```typescript
const COLORS = [
  "#1e1e1e", // black
  "#e03131", // red
  "#2f9e44", // green
  "#1971c2", // blue
  "#f08c00", // orange
  "#9c36b5", // purple
];
```

### Stroke Widths
```typescript
const STROKE_WIDTHS = [2, 4, 8, 12]; // pixels
```

## Testing

### Manual Testing Checklist

- [ ] Open scratchpad and draw freely
- [ ] Change colors and verify strokes change color
- [ ] Change stroke width and verify thickness changes
- [ ] Use eraser and verify strokes are removed
- [ ] Undo/Redo functionality works
- [ ] Clear board removes all content
- [ ] Connect to AI tutor
- [ ] Ask tutor to draw (e.g., "Draw a number line")
- [ ] Verify tutor's drawing appears on canvas
- [ ] Close and reopen scratchpad - should be empty

### Console Logs to Verify

```
✅ TutorDrawingHandler: Registered draw_on_scratchpad tool
✅ Sketch canvas ready for frame capture
✅ Question content found, starting capture
✅ TutorDrawingHandler: Added X strokes to scratchpad
```

## Future Improvements

- [ ] Add shape tools (rectangle, circle, arrow)
- [ ] Add text input on canvas
- [ ] Collaborative drawing (see partner's cursor)
- [ ] Drawing history/playback
- [ ] Export drawing as image
- [ ] Touch/stylus pressure sensitivity
