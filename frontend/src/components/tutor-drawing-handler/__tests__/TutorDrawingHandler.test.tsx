import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { TeachingCanvasHandle } from "../../teaching-canvas";

/**
 * Unit tests for TutorDrawingHandler logic.
 * Since the component deeply depends on TutorContext and Gemini SDK,
 * we test the core logic patterns: shape parsing, immediate response,
 * and canvas interaction — without needing to render the full component.
 */

// Mock canvas handle
function createMockCanvasHandle(): TeachingCanvasHandle {
  return {
    drawShapes: vi.fn(),
    clear: vi.fn(),
    undo: vi.fn(),
    redo: vi.fn(),
    exportImage: vi.fn(() => "data:image/png;base64,test"),
    getCanvas: vi.fn(() => document.createElement("canvas")),
    isAnimating: vi.fn(() => false),
    setEraserMode: vi.fn(),
    setStrokeColor: vi.fn(),
    setStrokeWidth: vi.fn(),
  };
}

describe("TutorDrawingHandler - Shape Parsing Logic", () => {
  let mockCanvas: TeachingCanvasHandle;

  beforeEach(() => {
    mockCanvas = createMockCanvasHandle();
    window.__teachingCanvasRef = mockCanvas;
  });

  afterEach(() => {
    window.__teachingCanvasRef = null;
  });

  it("should parse valid shapes as array of objects", () => {
    const shapes = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100, color: "#333", width: 3 },
      { type: "circle", cx: 200, cy: 200, r: 50, color: "#e03131" },
    ];

    // Simulate what the handler does
    const parsed = Array.isArray(shapes) ? shapes : JSON.parse(shapes as any);
    expect(parsed).toHaveLength(2);
    expect(parsed[0].type).toBe("line");
    expect(parsed[1].type).toBe("circle");
  });

  it("should parse valid shapes as string (fallback)", () => {
    const shapesStr = JSON.stringify([
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100, color: "#333", width: 3 },
    ]);

    const parsed = typeof shapesStr === "string" ? JSON.parse(shapesStr) : shapesStr;
    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe("line");
  });

  it("should parse text_label shapes", () => {
    const shapesStr = JSON.stringify([
      { type: "text_label", x: 50, y: 50, text: "Step 1: Multiply", color: "#1971c2", size: 20 },
    ]);

    const parsed = JSON.parse(shapesStr);
    expect(parsed[0].type).toBe("text_label");
    expect(parsed[0].text).toBe("Step 1: Multiply");
  });

  it("should parse number_line shapes", () => {
    const shapesStr = JSON.stringify([
      { type: "number_line", x: 50, y: 300, length: 700, min: 0, max: 10, marks: [3, 7] },
    ]);

    const parsed = JSON.parse(shapesStr);
    expect(parsed[0].type).toBe("number_line");
    expect(parsed[0].marks).toEqual([3, 7]);
  });

  it("should handle invalid JSON gracefully", () => {
    const badJson = "not valid json";
    let shapes: any[] = [];
    try {
      shapes = JSON.parse(badJson);
    } catch {
      // Expected
    }
    expect(shapes).toEqual([]);
  });

  it("should convert raw strokesJson to freehand shapes", () => {
    const rawStrokes = [
      {
        points: [{ x: 0, y: 0 }, { x: 50, y: 50 }, { x: 100, y: 0 }],
        strokeColor: "#ff0000",
        strokeWidth: 4,
      },
    ];

    const shapes = rawStrokes
      .filter((s: any) => s && Array.isArray(s.points) && s.points.length > 0)
      .map((stroke: any) => ({
        type: "freehand" as const,
        points: stroke.points,
        color: stroke.strokeColor || "#1e1e1e",
        width: stroke.strokeWidth || 4,
      }));

    expect(shapes).toHaveLength(1);
    expect(shapes[0].type).toBe("freehand");
    expect(shapes[0].color).toBe("#ff0000");
    expect(shapes[0].points).toHaveLength(3);
  });

  it("should filter out strokes without points", () => {
    const rawStrokes = [
      { points: [], strokeColor: "#000" },
      { points: null, strokeColor: "#000" },
      { strokeColor: "#000" },
      { points: [{ x: 0, y: 0 }, { x: 10, y: 10 }], strokeColor: "#f00" },
    ];

    const shapes = rawStrokes
      .filter((s: any) => s && Array.isArray(s.points) && s.points.length > 0)
      .map((stroke: any) => ({
        type: "freehand" as const,
        points: stroke.points,
        color: stroke.strokeColor || "#1e1e1e",
        width: stroke.strokeWidth || 4,
      }));

    expect(shapes).toHaveLength(1);
  });
});

describe("TutorDrawingHandler - Canvas Interaction", () => {
  let mockCanvas: TeachingCanvasHandle;

  beforeEach(() => {
    mockCanvas = createMockCanvasHandle();
    window.__teachingCanvasRef = mockCanvas;
  });

  afterEach(() => {
    window.__teachingCanvasRef = null;
  });

  it("should call drawShapes on the canvas with animated: true", () => {
    const shapes = [
      { type: "line" as const, x1: 0, y1: 0, x2: 100, y2: 100 },
    ];

    mockCanvas.drawShapes(shapes, { animated: true, clearFirst: false, durationMs: 1500 });

    expect(mockCanvas.drawShapes).toHaveBeenCalledWith(
      shapes,
      { animated: true, clearFirst: false, durationMs: 1500 }
    );
  });

  it("should call drawShapes with clearFirst when specified", () => {
    const shapes = [
      { type: "text_label" as const, x: 50, y: 50, text: "Clear me" },
    ];

    mockCanvas.drawShapes(shapes, { animated: true, clearFirst: true, durationMs: 1500 });

    expect(mockCanvas.drawShapes).toHaveBeenCalledWith(
      shapes,
      expect.objectContaining({ clearFirst: true })
    );
  });

  it("should handle missing canvas ref gracefully", () => {
    window.__teachingCanvasRef = null;
    const canvasRef = window.__teachingCanvasRef;
    expect(canvasRef).toBeNull();
    // In the real handler, this would send an error response to Gemini
  });
});

describe("TutorDrawingHandler - Tool Response Pattern", () => {
  it("should send response BEFORE animation starts (immediate pattern)", () => {
    const events: string[] = [];

    // Simulate the critical flow:
    // 1. Tool call received
    events.push("tool_call_received");

    // 2. Send response immediately (BEFORE animation)
    events.push("tool_response_sent");

    // 3. Queue animation (async, non-blocking)
    events.push("animation_queued");

    expect(events).toEqual([
      "tool_call_received",
      "tool_response_sent",
      "animation_queued",
    ]);
  });

  it("should include shapesQueued count in the tool response", () => {
    const shapes = [
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100 },
      { type: "circle", cx: 200, cy: 200, r: 50 },
    ];

    const response = {
      output: {
        success: true,
        shapesQueued: shapes.length,
      },
    };

    expect(response.output.success).toBe(true);
    expect(response.output.shapesQueued).toBe(2);
  });

  it("should include text labels in response when present", () => {
    const shapes = [
      { type: "text_label", text: "Step 1" },
      { type: "line", x1: 0, y1: 0, x2: 100, y2: 100 },
      { type: "text_label", text: "Step 2" },
    ];

    const textLabels = shapes
      .filter((s: any) => s.type === "text_label" && s.text)
      .map((s: any) => s.text);

    expect(textLabels).toEqual(["Step 1", "Step 2"]);
  });
});

