import type { RefObject } from "react";

type AnyRef = RefObject<any> | null | undefined;

export type ExternalStroke = {
  // common fields used by react-sketch-canvas
  path?: Array<[number, number]> | any;
  strokeColor?: string;
  strokeWidth?: number;
  drawMode?: boolean;
  [k: string]: any;
};

/**
 * Try to capture image from a react-sketch-canvas ref as a PNG data URL.
 * Falls back gracefully if methods are not available.
 */
export async function captureCanvasAsBase64(canvasRef: AnyRef): Promise<string | null> {
  try {
    const cr = canvasRef as RefObject<any>;
    if (!cr || !cr.current) return null;

    // Preferred API: react-sketch-canvas exportImage
    if (typeof cr.current.exportImage === "function") {
      // exportImage can return a promise or value depending on version
      const result = cr.current.exportImage("png");
      if (result && typeof result.then === "function") {
        return await result as string;
      }
      return result as string;
    }

    // Fallback: attempt to find an HTMLCanvasElement inside the component
    const el: HTMLElement | null = cr.current instanceof HTMLElement ? cr.current : (cr.current?.canvas || null);
    const canvas = el instanceof HTMLCanvasElement ? el : el?.querySelector?.("canvas");
    if (canvas && typeof canvas.toDataURL === "function") {
      return canvas.toDataURL("image/png");
    }

    return null;
  } catch (err) {
    console.error("captureCanvasAsBase64 error", err);
    return null;
  }
}

/**
 * Programmatically draw a set of strokes on a react-sketch-canvas instance.
 * This helper tries multiple method names to remain compatible across versions.
 * Expected `strokes` format: array of paths compatible with react-sketch-canvas `loadPaths`.
 */
export async function drawOnScratchpad(canvasRef: AnyRef, strokes: ExternalStroke[] = []): Promise<void> {
  try {
    if (!canvasRef || !canvasRef.current) return;
    const inst = canvasRef.current;

    // Sanitize incoming strokes: ensure drawMode is explicitly true
    const sanitized: ExternalStroke[] = (strokes || []).map((s) => ({
      ...s,
      drawMode: true,
    }));

    console.log('Loading paths to canvas...', sanitized.length);

    // Preferred: loadPaths
    if (typeof inst.loadPaths === "function") {
      const res = inst.loadPaths(sanitized);
      if (res && typeof res.then === 'function') await res;
      return;
    }

    // Alternative: importPaths / fromJSON
    if (typeof inst.importPaths === "function") {
      const res = inst.importPaths(sanitized);
      if (res && typeof res.then === 'function') await res;
      return;
    }

    if (typeof inst.fromJSON === "function") {
      const res = inst.fromJSON({ paths: sanitized });
      if (res && typeof res.then === 'function') await res;
      return;
    }

    // As a last resort, try to draw via the low-level canvas element (not ideal)
    const el: HTMLElement | null = inst instanceof HTMLElement ? inst : (inst?.canvas || null);
    const canvas = el instanceof HTMLCanvasElement ? el : el?.querySelector?.("canvas");
    if (!canvas) return;
    const ctx = (canvas as HTMLCanvasElement).getContext("2d");
    if (!ctx) return;

    sanitized.forEach((s) => {
      try {
        const color = s.strokeColor || s.brushColor || "#000";
        const width = s.strokeWidth || s.brushRadius || 2;
        ctx.beginPath();
        // handle multiple path formats
        const pts = Array.isArray(s.path) ? s.path : s.points || s.pointsArray || [];
        if (Array.isArray(pts) && pts.length) {
          const first = pts[0];
          // pts might be [x,y] pairs or {x,y}
          if (Array.isArray(first)) {
            ctx.moveTo(first[0], first[1]);
            pts.forEach((p: any) => ctx.lineTo(p[0], p[1]));
          } else {
            ctx.moveTo(first.x, first.y);
            pts.forEach((p: any) => ctx.lineTo(p.x, p.y));
          }
          ctx.stroke();
        }
      } catch (e) {
        // ignore per-stroke errors
      }
    });
  } catch (err) {
    console.error("drawOnScratchpad error", err);
  }
}

export default captureCanvasAsBase64;
