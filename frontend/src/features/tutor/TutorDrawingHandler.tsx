import React, { useEffect } from "react";

type DrawingEventDetail = {
  strokes: any[];
};

/**
 * A small handler that listens for drawing events and forwards them to the global scratchpad handle.
 * Other parts of the app can dispatch a `CustomEvent('tutor-drawing', { detail: { strokes } })`
 * to render strokes on the scratchpad.
 */
export default function TutorDrawingHandler() {
  useEffect(() => {
    const onDrawing = (e: Event) => {
      try {
        const ce = e as CustomEvent<DrawingEventDetail>;
        const strokes = ce?.detail?.strokes;
        if (!strokes) return;
        const handle = (window as any).__scratchpadHandle;
        if (handle && typeof handle.drawExternal === "function") {
          handle.drawExternal(strokes);
        }
      } catch (err) {
        // ignore
      }
    };

    window.addEventListener("tutor-drawing", onDrawing as EventListener);
    return () => window.removeEventListener("tutor-drawing", onDrawing as EventListener);
  }, []);

  return null;
}

/** Helper to trigger a drawing event programmatically (for tests) */
export function triggerDrawing(strokes: any[]) {
  const ev = new CustomEvent<DrawingEventDetail>("tutor-drawing", { detail: { strokes } });
  window.dispatchEvent(ev as Event);
}
