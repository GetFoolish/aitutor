# Scratchpad AI Drawing — Setup & Usage

## Overview
The Scratchpad component (see [src/components/scratchpad/Scratchpad.tsx](src/components/scratchpad/Scratchpad.tsx)) uses `react-sketch-canvas` to provide an interactive drawing surface with bi-directional AI integration:

- **AI Drawing:** programmatic strokes sent into the canvas (via `drawExternal`).
- **Vision Capture:** snapshotting the canvas (via `capture`) for vision/analysis pipelines.

The component exposes a typed handle (`ScratchpadHandle`) via `ref` for these integrations.

---

## Installation
Install the canvas dependency:

```sh
npm install react-sketch-canvas
```

(Also ensure your app bundles and styles for Tailwind/CSS so the canvas fills its container.)

---

## Component API (via ref)
Attach a ref to the `<Scratchpad />` component and call methods on the handle:

- `ScratchpadHandle`
  - `capture(): Promise<string>`
    - Returns a Base64-encoded PNG image string of the current canvas.

  - `drawExternal(strokes: Stroke[]): Promise<void>`
    - Programmatically draws an array of stroke objects onto the canvas.

Refer to [src/components/scratchpad/Scratchpad.tsx](src/components/scratchpad/Scratchpad.tsx) for the concrete TypeScript definitions.

---

## Stroke Data Structure
Each stroke object must include the following fields (example shape):

- `drawMode: true` (required — `react-sketch-canvas` expects explicit draw mode)
- `strokeColor: string` (CSS color string, e.g. `"red"` or `"#ff0000"`)
- `strokeWidth: number` (pixel width)
- `paths: Array<[number, number]>` (ordered array of points; coordinates in canvas pixels)
- Optional: `id`, `brush`, and other metadata allowed by your implementation

Example stroke (Red Box from 100,100 to 300,300):

```js
[
  {
    drawMode: true,
    strokeColor: 'red',
    strokeWidth: 2,
    // path of rectangle perimeter (closed)
    paths: [
      [100, 100],
      [300, 100],
      [300, 300],
      [100, 300],
      [100, 100]
    ]
  }
]
```

Note: The implementation in [`Scratchpad`](src/components/scratchpad/Scratchpad.tsx) sanitizes incoming strokes to enforce `drawMode: true` before loading them into the canvas.

---

## Manual Testing Guide

1. Expose the handle for quick console testing (temporary — use only during development). Example change in your app to mount the ref and attach it to `window`:

```tsx
// Quick dev snippet (do NOT keep in production)
const ref = useRef<ScratchpadHandle | null>(null);
useEffect(() => {
  (window as any).__scratchpadHandle = ref.current;
  return () => { delete (window as any).__scratchpadHandle; };
}, []);
<Scratchpad ref={ref} />
```

2. From the browser console:

- Test AI Drawing (Red Box):
```js
window.__scratchpadHandle?.drawExternal([
  {
    drawMode: true,
    strokeColor: 'red',
    strokeWidth: 2,
    paths: [[100,100],[300,100],[300,300],[100,300],[100,100]]
  }
]);
```

- Test Vision Capture:
```js
// returns a base64 image string
await window.__scratchpadHandle?.capture();
```

(If you implemented a temporary helper like `window.testDrawOnScratchpad()`, you can call that instead.)

---

## Troubleshooting

- **Invisible drawing / 0-height canvas:**
  - Ensure the Scratchpad parent container has explicit height. The canvas relies on its container sizing; without a defined height the canvas can collapse to 0px.
  - See the component implementation: [src/components/scratchpad/Scratchpad.tsx](src/components/scratchpad/Scratchpad.tsx). The `<ReactSketchCanvas />` is configured with `width="100%"` and `height="100%"` — confirm the parent element supplies the pixel bounds (e.g. `w-[800px] h-[600px]` or CSS height).

- If `drawExternal` appears to succeed but nothing shows, verify:
  - Each stroke has `drawMode: true`.
  - `strokeColor` and `strokeWidth` are valid.
  - Path coordinates are within the canvas bounds.

---

## References
- Component source: [src/components/scratchpad/Scratchpad.tsx](src/components/scratchpad/Scratchpad.tsx)
- App entry (where Scratchpad is mounted): [src/App.tsx](src/App.tsx)
- Exposed handle type: `ScratchpadHandle` (see component source)
