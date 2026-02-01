# ✏️ Scratchpad Feature

A tldraw-based drawing canvas for students to work through problems.

## Quick Start

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Start the frontend
npm run dev

# 3. Open the demo page
open http://localhost:3000/test/demo
```

## Demo Page

**URL**: `http://localhost:3000/test/demo`

Shows the scratchpad alongside a sample math question. Use this to verify the feature works.

## Components

### `src/components/scratchpad/Scratchpad.tsx`
The main scratchpad component using tldraw.

Basic usage:
```tsx
import Scratchpad from '@/components/scratchpad/Scratchpad';

function MyComponent() {
  return <Scratchpad />;
}
```

### `src/components/scratchpad/ScratchpadDemo.tsx`
Demo page showing scratchpad with a sample question.

**Route**: `/test/demo`

## Features

- ✏️ **Drawing tools**: Pencil, shapes, text, arrows
- 🔄 **Undo/Redo**: Full history support  
- 🖐️ **Pan & Zoom**: Navigate large drawings
- 📷 **Export**: Save drawings as images
- 👁️ **Show/Hide toggle**: Minimize when not needed

## Dependencies

- `tldraw` - Canvas/drawing library
- React 18+

## Testing

1. Open demo page: `http://localhost:3000/test/demo`
2. Select the Draw tool (pencil icon)
3. Draw on the canvas
4. Try Text tool to add labels
5. Test Hide/Show Scratchpad toggle
6. Test undo/redo

## Integration Example

```tsx
import React, { useState } from 'react';
import { Tldraw } from 'tldraw';
import 'tldraw/tldraw.css';

function QuestionWithScratchpad({ question }) {
  const [showScratchpad, setShowScratchpad] = useState(true);

  return (
    <div style={{ display: 'flex', gap: '24px' }}>
      <div className="question-panel">
        <h2>{question.title}</h2>
        <p>{question.content}</p>
      </div>
      
      {showScratchpad && (
        <div style={{ width: '400px', height: '500px' }}>
          <Tldraw />
        </div>
      )}
    </div>
  );
}
```

## Notes

- Uses tldraw (not Excalidraw) for better stability
- The scratchpad state is local to each session
- Drawing data can be exported for AI analysis if needed
