import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React, { createRef } from "react";
import { TeachingCanvas, TeachingCanvasHandle } from "../TeachingCanvas";

describe("TeachingCanvas", () => {
  it("should render a canvas element", () => {
    const { container } = render(<TeachingCanvas />);
    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();
  });

  it("should use default dimensions 800x600", () => {
    const { container } = render(<TeachingCanvas />);
    const canvas = container.querySelector("canvas") as HTMLCanvasElement;
    expect(canvas.width).toBe(800);
    expect(canvas.height).toBe(600);
  });

  it("should accept custom dimensions", () => {
    const { container } = render(<TeachingCanvas width={1024} height={768} />);
    const canvas = container.querySelector("canvas") as HTMLCanvasElement;
    expect(canvas.width).toBe(1024);
    expect(canvas.height).toBe(768);
  });

  describe("Imperative API via ref", () => {
    let ref: React.RefObject<TeachingCanvasHandle | null>;

    beforeEach(() => {
      ref = createRef<TeachingCanvasHandle>();
      render(<TeachingCanvas ref={ref} />);
    });

    it("should expose drawShapes method", () => {
      expect(ref.current?.drawShapes).toBeDefined();
      expect(typeof ref.current?.drawShapes).toBe("function");
    });

    it("should expose clear method", () => {
      expect(ref.current?.clear).toBeDefined();
      expect(typeof ref.current?.clear).toBe("function");
    });

    it("should expose undo/redo methods", () => {
      expect(ref.current?.undo).toBeDefined();
      expect(ref.current?.redo).toBeDefined();
    });

    it("should expose exportImage method that returns a data URL", () => {
      const dataUrl = ref.current?.exportImage();
      expect(dataUrl).toBeDefined();
      expect(typeof dataUrl).toBe("string");
    });

    it("should expose getCanvas method", () => {
      const canvas = ref.current?.getCanvas();
      expect(canvas).toBeInstanceOf(HTMLCanvasElement);
    });

    it("should expose isAnimating method", () => {
      expect(ref.current?.isAnimating()).toBe(false);
    });

    it("should expose setEraserMode", () => {
      expect(() => ref.current?.setEraserMode(true)).not.toThrow();
      expect(() => ref.current?.setEraserMode(false)).not.toThrow();
    });

    it("should expose setStrokeColor", () => {
      expect(() => ref.current?.setStrokeColor("#ff0000")).not.toThrow();
    });

    it("should expose setStrokeWidth", () => {
      expect(() => ref.current?.setStrokeWidth(8)).not.toThrow();
    });

    it("should drawShapes with animated option", () => {
      expect(() =>
        ref.current?.drawShapes(
          [{ type: "line", x1: 0, y1: 0, x2: 100, y2: 100, color: "#000" }],
          { animated: true, durationMs: 500 }
        )
      ).not.toThrow();
    });

    it("should drawShapes with instant (non-animated) option", () => {
      expect(() =>
        ref.current?.drawShapes(
          [{ type: "text_label", x: 50, y: 50, text: "Test", size: 20 }],
          { animated: false }
        )
      ).not.toThrow();
    });

    it("should drawShapes with clearFirst option", () => {
      // Add some shapes first
      ref.current?.drawShapes(
        [{ type: "circle", cx: 100, cy: 100, r: 50 }],
        { animated: false }
      );

      // Now draw with clearFirst
      expect(() =>
        ref.current?.drawShapes(
          [{ type: "rect", x: 0, y: 0, w: 200, h: 100 }],
          { animated: false, clearFirst: true }
        )
      ).not.toThrow();
    });

    it("should clear all content", () => {
      ref.current?.drawShapes(
        [{ type: "line", x1: 0, y1: 0, x2: 100, y2: 100 }],
        { animated: false }
      );
      expect(() => ref.current?.clear()).not.toThrow();
    });

    it("should handle undo/redo gracefully when empty", () => {
      expect(() => ref.current?.undo()).not.toThrow();
      expect(() => ref.current?.redo()).not.toThrow();
    });
  });

  describe("Pointer events (student drawing)", () => {
    it("should handle pointer down, move, and up events", () => {
      const { container } = render(<TeachingCanvas />);
      const canvas = container.querySelector("canvas")!;

      // Simulate drawing a stroke
      fireEvent.pointerDown(canvas, { clientX: 50, clientY: 50, pointerId: 1 });
      fireEvent.pointerMove(canvas, { clientX: 100, clientY: 100, pointerId: 1 });
      fireEvent.pointerMove(canvas, { clientX: 150, clientY: 80, pointerId: 1 });
      fireEvent.pointerUp(canvas, { clientX: 150, clientY: 80, pointerId: 1 });

      // No errors should occur
    });

    it("should call onContentChange when a stroke is completed", () => {
      const onContentChange = vi.fn();
      const { container } = render(
        <TeachingCanvas onContentChange={onContentChange} />
      );
      const canvas = container.querySelector("canvas")!;

      fireEvent.pointerDown(canvas, { clientX: 50, clientY: 50, pointerId: 1 });
      fireEvent.pointerMove(canvas, { clientX: 100, clientY: 100, pointerId: 1 });
      fireEvent.pointerUp(canvas, { clientX: 100, clientY: 100, pointerId: 1 });

      expect(onContentChange).toHaveBeenCalled();
    });

    it("should handle pointerLeave as stroke end", () => {
      const { container } = render(<TeachingCanvas />);
      const canvas = container.querySelector("canvas")!;

      fireEvent.pointerDown(canvas, { clientX: 50, clientY: 50, pointerId: 1 });
      fireEvent.pointerMove(canvas, { clientX: 100, clientY: 100, pointerId: 1 });
      // Leave the canvas - should end the stroke
      fireEvent.pointerLeave(canvas, { clientX: 100, clientY: 100, pointerId: 1 });

      // No errors
    });
  });
});

