import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { DrawingAnimator, ShapeDef } from "../DrawingAnimator";

describe("DrawingAnimator", () => {
  let animator: DrawingAnimator;
  let mockCtx: CanvasRenderingContext2D;
  let redrawCb: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    animator = new DrawingAnimator();
    // Get a mock context from a canvas element (mocked in test-setup.ts)
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 600;
    mockCtx = canvas.getContext("2d")!;
    redrawCb = vi.fn();
    animator.attach(mockCtx, redrawCb);
  });

  afterEach(() => {
    animator.detach();
  });

  it("should start with isAnimating = false", () => {
    expect(animator.isAnimating).toBe(false);
  });

  it("should start animating when shapes are enqueued", () => {
    const shapes: ShapeDef[] = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100, color: "#000", width: 2 },
    ];
    animator.enqueue({ shapes, durationMs: 100 });
    expect(animator.isAnimating).toBe(true);
  });

  it("should accept multiple shape types in a batch", () => {
    const shapes: ShapeDef[] = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100 },
      { type: "rect", x: 50, y: 50, w: 100, h: 80 },
      { type: "circle", cx: 200, cy: 200, r: 50 },
      { type: "arrow", x1: 0, y1: 300, x2: 200, y2: 300 },
      { type: "text_label", x: 10, y: 10, text: "Hello", size: 20 },
      { type: "number_line", x: 50, y: 400, length: 500, min: 0, max: 10, marks: [3, 7] },
      { type: "freehand", points: [{ x: 0, y: 0 }, { x: 50, y: 50 }, { x: 100, y: 0 }] },
    ];
    animator.enqueue({ shapes, durationMs: 200 });
    expect(animator.isAnimating).toBe(true);
  });

  it("should stop all animations and clear the queue", () => {
    const shapes: ShapeDef[] = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100 },
    ];
    animator.enqueue({ shapes, durationMs: 5000 });
    expect(animator.isAnimating).toBe(true);

    animator.stop();
    expect(animator.isAnimating).toBe(false);
    expect(animator.completedCount).toBe(0);
  });

  it("should finishAll — move all queued shapes to completed immediately", () => {
    const shapes: ShapeDef[] = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100 },
      { type: "circle", cx: 200, cy: 200, r: 50 },
    ];
    animator.enqueue({ shapes, durationMs: 5000 });
    animator.finishAll();

    expect(animator.isAnimating).toBe(false);
    expect(animator.completedCount).toBe(2);
  });

  it("should clearCompleted to reset completed shapes", () => {
    const shapes: ShapeDef[] = [
      { type: "text_label", x: 10, y: 10, text: "Test" },
    ];
    animator.enqueue({ shapes, durationMs: 100 });
    animator.finishAll();
    expect(animator.completedCount).toBe(1);

    animator.clearCompleted();
    expect(animator.completedCount).toBe(0);
  });

  it("should render a line shape at full progress", () => {
    const shape: ShapeDef = { type: "line", x1: 10, y1: 20, x2: 100, y2: 200, color: "#ff0000", width: 3 };
    animator.renderShape(mockCtx, shape, 1);

    expect(mockCtx.beginPath).toHaveBeenCalled();
    expect(mockCtx.moveTo).toHaveBeenCalledWith(10, 20);
    expect(mockCtx.lineTo).toHaveBeenCalledWith(100, 200);
    expect(mockCtx.stroke).toHaveBeenCalled();
  });

  it("should render a line shape at partial progress", () => {
    const shape: ShapeDef = { type: "line", x1: 0, y1: 0, x2: 100, y2: 0, color: "#000", width: 2 };
    animator.renderShape(mockCtx, shape, 0.5);

    expect(mockCtx.lineTo).toHaveBeenCalledWith(50, 0); // halfway
  });

  it("should render a circle shape", () => {
    const shape: ShapeDef = { type: "circle", cx: 100, cy: 100, r: 50, color: "#00f", width: 2 };
    animator.renderShape(mockCtx, shape, 1);

    expect(mockCtx.arc).toHaveBeenCalled();
    expect(mockCtx.stroke).toHaveBeenCalled();
  });

  it("should render a rect shape", () => {
    const shape: ShapeDef = { type: "rect", x: 10, y: 10, w: 200, h: 100, color: "#0f0", width: 2 };
    animator.renderShape(mockCtx, shape, 1);

    expect(mockCtx.beginPath).toHaveBeenCalled();
    expect(mockCtx.stroke).toHaveBeenCalled();
  });

  it("should render an arrow shape", () => {
    const shape: ShapeDef = { type: "arrow", x1: 0, y1: 0, x2: 100, y2: 0, color: "#f00", width: 3 };
    animator.renderShape(mockCtx, shape, 1);

    expect(mockCtx.stroke).toHaveBeenCalled();
  });

  it("should render text with typewriter effect", () => {
    const shape: ShapeDef = { type: "text_label", x: 50, y: 50, text: "Hello World", size: 24, color: "#333" };

    // At 50% progress, should show ~6 of 11 characters
    animator.renderShape(mockCtx, shape, 0.5);
    expect(mockCtx.fillText).toHaveBeenCalledWith("Hello ", 50, 50);

    // At 100% progress, show all
    vi.mocked(mockCtx.fillText).mockClear();
    animator.renderShape(mockCtx, shape, 1);
    expect(mockCtx.fillText).toHaveBeenCalledWith("Hello World", 50, 50);
  });

  it("should render a number line", () => {
    const shape: ShapeDef = {
      type: "number_line",
      x: 50, y: 300, length: 700, min: 0, max: 10, marks: [3, 7],
      color: "#333", width: 2,
    };
    animator.renderShape(mockCtx, shape, 1);

    // Should have drawn the main axis, tick marks, and highlight marks
    expect(mockCtx.beginPath).toHaveBeenCalled();
    expect(mockCtx.stroke).toHaveBeenCalled();
    expect(mockCtx.fillText).toHaveBeenCalled();
  });

  it("should render freehand strokes", () => {
    const shape: ShapeDef = {
      type: "freehand",
      points: [{ x: 0, y: 0 }, { x: 50, y: 50 }, { x: 100, y: 0 }],
      color: "#000", width: 3,
    };
    animator.renderShape(mockCtx, shape, 1);

    expect(mockCtx.beginPath).toHaveBeenCalled();
    expect(mockCtx.moveTo).toHaveBeenCalledWith(0, 0);
    expect(mockCtx.stroke).toHaveBeenCalled();
  });

  it("should render completed shapes on request", () => {
    const shapes: ShapeDef[] = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100 },
      { type: "text_label", x: 10, y: 10, text: "Done" },
    ];
    animator.enqueue({ shapes, durationMs: 100 });
    animator.finishAll();

    const spy = vi.spyOn(animator, "renderShape");
    animator.renderCompleted(mockCtx);
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it("should handle concurrent batches", () => {
    animator.enqueue({
      shapes: [{ type: "line", x1: 0, y1: 0, x2: 100, y2: 100 }],
      durationMs: 1000,
    });
    animator.enqueue({
      shapes: [{ type: "circle", cx: 200, cy: 200, r: 50 }],
      durationMs: 1000,
    });

    expect(animator.isAnimating).toBe(true);
    animator.finishAll();
    expect(animator.completedCount).toBe(2);
  });

  it("should handle empty shapes array", () => {
    animator.enqueue({ shapes: [], durationMs: 100 });
    // Should not crash; might still trigger animation loop briefly
    expect(animator.completedCount).toBe(0);
  });

  it("should handle shapes with default values (missing optional props)", () => {
    const shapes: ShapeDef[] = [
      { type: "line" }, // all optional props missing
      { type: "circle" },
      { type: "rect" },
      { type: "text_label" },
      { type: "arrow" },
      { type: "freehand" },
      { type: "number_line" },
    ];

    // Should not throw
    for (const shape of shapes) {
      expect(() => animator.renderShape(mockCtx, shape, 1)).not.toThrow();
    }
  });

  it("should detach cleanly", () => {
    animator.enqueue({
      shapes: [{ type: "line", x1: 0, y1: 0, x2: 100, y2: 100 }],
      durationMs: 5000,
    });
    animator.detach();
    expect(animator.isAnimating).toBe(false);
  });
});

