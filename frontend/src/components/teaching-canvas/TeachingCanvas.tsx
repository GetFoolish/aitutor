/**
 * TeachingCanvas - Native HTML5 Canvas whiteboard component
 *
 * Replaces react-sketch-canvas with a raw Canvas 2D implementation
 * that supports:
 * - Student freehand drawing (pen, eraser, colors, widths)
 * - AI-driven progressive shape animation via DrawingAnimator
 * - Real text rendering via ctx.fillText()
 * - Undo / redo via path history
 * - Export for frame capture
 *
 * The public API is exposed via forwardRef + useImperativeHandle so
 * both the Scratchpad toolbar and TutorDrawingHandler can drive it.
 */

import React, {
  useRef,
  useEffect,
  useCallback,
  useImperativeHandle,
  forwardRef,
  useState,
} from "react";
import { DrawingAnimator, ShapeDef, DrawBatch } from "./DrawingAnimator";

// ──────────────────────────────────────────────────────────
// Public handle type
// ──────────────────────────────────────────────────────────

export interface TeachingCanvasHandle {
  /** Draw shapes with optional progressive animation */
  drawShapes(shapes: ShapeDef[], options?: { animated?: boolean; durationMs?: number; clearFirst?: boolean }): void;
  /** Clear the entire canvas */
  clear(): void;
  /** Undo the last student stroke */
  undo(): void;
  /** Redo the last undone student stroke */
  redo(): void;
  /** Export as data URL (default png) */
  exportImage(format?: "png" | "jpeg"): string;
  /** Get the raw canvas element */
  getCanvas(): HTMLCanvasElement | null;
  /** Check if animator is active */
  isAnimating(): boolean;
  /** Set eraser mode */
  setEraserMode(on: boolean): void;
  /** Set stroke color */
  setStrokeColor(color: string): void;
  /** Set stroke width */
  setStrokeWidth(width: number): void;
}

// ──────────────────────────────────────────────────────────
// Internal types
// ──────────────────────────────────────────────────────────

interface Stroke {
  points: Array<{ x: number; y: number }>;
  color: string;
  width: number;
  isEraser: boolean;
}

interface StaticShape {
  shape: ShapeDef;
}

interface TeachingCanvasProps {
  /** Canvas width in CSS pixels */
  width?: number;
  /** Canvas height in CSS pixels */
  height?: number;
  /** Background color */
  backgroundColor?: string;
  /** Called when the canvas content changes (for parent awareness) */
  onContentChange?: () => void;
}

// ──────────────────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────────────────

const TeachingCanvasInner: React.ForwardRefRenderFunction<
  TeachingCanvasHandle,
  TeachingCanvasProps
> = (
  {
    width = 800,
    height = 600,
    backgroundColor = "#ffffff",
    onContentChange,
  },
  ref
) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animatorRef = useRef<DrawingAnimator>(new DrawingAnimator());

  // Student drawing state
  const isDrawingRef = useRef(false);
  const currentStrokeRef = useRef<Stroke | null>(null);
  const strokeColorRef = useRef("#1e1e1e");
  const strokeWidthRef = useRef(4);
  const eraserModeRef = useRef(false);

  // History for undo/redo
  const strokeHistoryRef = useRef<Stroke[]>([]);
  const redoStackRef = useRef<Stroke[]>([]);

  // Static shapes (AI shapes that are fully rendered)
  const staticShapesRef = useRef<StaticShape[]>([]);

  // Force re-render counter (for when we need React to update)
  const [, setRenderTick] = useState(0);

  // ──────────────────────────────────────────────────────────
  // Full canvas redraw
  // ──────────────────────────────────────────────────────────

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 1) Render completed student strokes
    for (const stroke of strokeHistoryRef.current) {
      renderStroke(ctx, stroke);
    }

    // 2) Render static AI shapes (completed animations)
    for (const { shape } of staticShapesRef.current) {
      animatorRef.current.renderShape(ctx, shape, 1);
    }

    // 3) Render animator's completed shapes (from current batch)
    animatorRef.current.renderCompleted(ctx);

    // 4) Render in-progress student stroke
    if (currentStrokeRef.current && currentStrokeRef.current.points.length > 1) {
      renderStroke(ctx, currentStrokeRef.current);
    }
  }, [backgroundColor]);

  // ──────────────────────────────────────────────────────────
  // Stroke renderer
  // ──────────────────────────────────────────────────────────

  function renderStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
    if (stroke.points.length < 2) return;

    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (stroke.isEraser) {
      ctx.globalCompositeOperation = "destination-out";
      ctx.strokeStyle = "rgba(0,0,0,1)";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = stroke.color;
    }
    ctx.lineWidth = stroke.width;

    ctx.beginPath();
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    for (let i = 1; i < stroke.points.length; i++) {
      ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
    }
    ctx.stroke();
    ctx.restore();
  }

  // ──────────────────────────────────────────────────────────
  // Setup animator
  // ──────────────────────────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const animator = animatorRef.current;
    animator.attach(ctx, () => {
      // On each animation frame, do a full redraw
      redraw();
    });

    // Initial draw
    redraw();

    return () => {
      animator.detach();
    };
  }, [redraw]);

  // ──────────────────────────────────────────────────────────
  // Pointer events (student drawing)
  // ──────────────────────────────────────────────────────────

  const getCanvasPoint = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    },
    []
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const point = getCanvasPoint(e);
      isDrawingRef.current = true;
      currentStrokeRef.current = {
        points: [point],
        color: strokeColorRef.current,
        width: strokeWidthRef.current,
        isEraser: eraserModeRef.current,
      };

      // Clear redo stack when starting a new stroke
      redoStackRef.current = [];

      // Capture pointer for smooth drawing even outside canvas
      canvasRef.current?.setPointerCapture?.(e.pointerId);
    },
    [getCanvasPoint]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawingRef.current || !currentStrokeRef.current) return;
      const point = getCanvasPoint(e);
      currentStrokeRef.current.points.push(point);
      redraw();
    },
    [getCanvasPoint, redraw]
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawingRef.current || !currentStrokeRef.current) return;
      isDrawingRef.current = false;

      // Only save if there are enough points
      if (currentStrokeRef.current.points.length > 1) {
        strokeHistoryRef.current.push(currentStrokeRef.current);
        onContentChange?.();
      }

      currentStrokeRef.current = null;
      canvasRef.current?.releasePointerCapture?.(e.pointerId);
      redraw();
    },
    [redraw, onContentChange]
  );

  // ──────────────────────────────────────────────────────────
  // Imperative API
  // ──────────────────────────────────────────────────────────

  useImperativeHandle(ref, () => ({
    drawShapes(
      shapes: ShapeDef[],
      options?: { animated?: boolean; durationMs?: number; clearFirst?: boolean }
    ) {
      const animated = options?.animated ?? true;
      const durationMs = options?.durationMs ?? 1500;
      const clearFirst = options?.clearFirst ?? false;

      if (clearFirst) {
        strokeHistoryRef.current = [];
        redoStackRef.current = [];
        staticShapesRef.current = [];
        animatorRef.current.stop();
        animatorRef.current.clearCompleted();
      }

      if (animated) {
        animatorRef.current.enqueue({
          shapes,
          durationMs,
          clearFirst: false, // Already handled above
        });
      } else {
        // Instant render: add directly to static shapes
        for (const shape of shapes) {
          staticShapesRef.current.push({ shape });
        }
        redraw();
        onContentChange?.();
      }
    },

    clear() {
      strokeHistoryRef.current = [];
      redoStackRef.current = [];
      staticShapesRef.current = [];
      animatorRef.current.stop();
      animatorRef.current.clearCompleted();
      redraw();
      onContentChange?.();
    },

    undo() {
      const last = strokeHistoryRef.current.pop();
      if (last) {
        redoStackRef.current.push(last);
        redraw();
        onContentChange?.();
      }
    },

    redo() {
      const last = redoStackRef.current.pop();
      if (last) {
        strokeHistoryRef.current.push(last);
        redraw();
        onContentChange?.();
      }
    },

    exportImage(format: "png" | "jpeg" = "png"): string {
      const canvas = canvasRef.current;
      if (!canvas) return "";
      return canvas.toDataURL(`image/${format}`);
    },

    getCanvas(): HTMLCanvasElement | null {
      return canvasRef.current;
    },

    isAnimating(): boolean {
      return animatorRef.current.isAnimating;
    },

    setEraserMode(on: boolean) {
      eraserModeRef.current = on;
      setRenderTick((t) => t + 1);
    },

    setStrokeColor(color: string) {
      strokeColorRef.current = color;
      eraserModeRef.current = false;
      setRenderTick((t) => t + 1);
    },

    setStrokeWidth(width: number) {
      strokeWidthRef.current = width;
      setRenderTick((t) => t + 1);
    },
  }), [redraw, onContentChange]);

  // ──────────────────────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────────────────────

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        width: "100%",
        height: "100%",
        display: "block",
        touchAction: "none",
        cursor: eraserModeRef.current ? "crosshair" : "default",
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
    />
  );
};

export const TeachingCanvas = forwardRef(TeachingCanvasInner);
export default TeachingCanvas;

