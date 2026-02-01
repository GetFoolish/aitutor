# 📝 Scratchpad Feature

A tldraw-based drawing canvas for students to work through problems.

## Quick Start

```bash
cd frontend
npm run dev
# Open http://localhost:3000/test/demo
```

## Demo Page

**URL**: `http://localhost:3000/test/demo`

Shows the scratchpad alongside a sample math question. Use this to verify the feature works.

## Components

### `src/components/scratchpad/Scratchpad.tsx`
The main scratchpad component using tldraw.

**Props:**
- `onCapture?: (imageData: string) => void` - Callback when canvas is captured
- `width?: string` - Canvas width (default: 100%)
- `height?: string` - Canvas height (default: 400px)

### `src/components/scratchpad/ScratchpadDemo.tsx`
Demo page showing scratchpad with a sample question.

**Route**: `/test/demo`

## Features

- ✏️ **Drawing tools**: Pencil, shapes, text, arrows
- 🔄 **Undo/Redo**: Full history support
- 🗑️ **Clear Board**: One-click canvas reset
- 👁️ **Show/Hide toggle**: Minimize when not needed
- 📷 **Capture**: Export canvas as image (for AI analysis)

## Integration Example

```tsx
import { Scratchpad } from '@/components/scratchpad/Scratchpad';

function QuestionPage() {
  const handleCapture = (imageData: string) => {
    // Send to AI for analysis
    console.log('Canvas captured:', imageData);
  };

  return (
    <div className="question-layout">
      <QuestionDisplay question={question} />
      <Scratchpad onCapture={handleCapture} />
    </div>
  );
}
```

## Styling

The scratchpad uses the teachr design system:
- **Header**: Peach background (`#FFF5E6`)
- **Canvas**: White with full tldraw toolbar
- **Clear button**: Red accent for visibility

## Dependencies

- `tldraw` - Canvas/drawing library
- React 18+

## Testing

1. Open demo page: `http://localhost:3000/test/demo`
2. Select the Draw tool (pencil icon)
3. Draw on the canvas
4. Try Text tool to add labels
5. Test Clear Board button
6. Test Hide/Show Scratchpad toggle
