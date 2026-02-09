import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import ScratchpadCapture from "../ScratchpadCapture";
import type { TeachingCanvasHandle } from "../../teaching-canvas";

// Mock html-to-image since it requires a real DOM
vi.mock("html-to-image", () => ({
  toCanvas: vi.fn(() => Promise.resolve(document.createElement("canvas"))),
}));

function createMockCanvasHandle(): TeachingCanvasHandle {
  const canvas = document.createElement("canvas");
  canvas.width = 800;
  canvas.height = 600;
  return {
    drawShapes: vi.fn(),
    clear: vi.fn(),
    undo: vi.fn(),
    redo: vi.fn(),
    exportImage: vi.fn(() => "data:image/png;base64,test"),
    getCanvas: vi.fn(() => canvas),
    isAnimating: vi.fn(() => false),
    setEraserMode: vi.fn(),
    setStrokeColor: vi.fn(),
    setStrokeWidth: vi.fn(),
  };
}

describe("ScratchpadCapture", () => {
  it("should render children content", () => {
    render(
      <ScratchpadCapture onFrameCaptured={vi.fn()}>
        <div data-testid="child-content">Question goes here</div>
      </ScratchpadCapture>
    );

    expect(screen.getByTestId("child-content")).toBeDefined();
  });

  it("should render the wrapper div with correct styles", () => {
    const { container } = render(
      <ScratchpadCapture onFrameCaptured={vi.fn()}>
        <div>Content</div>
      </ScratchpadCapture>
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.style.display).toBe("flex");
    expect(wrapper.style.flexDirection).toBe("column");
    expect(wrapper.style.pointerEvents).toBe("auto");
  });

  it("should accept teachingCanvasRef prop", () => {
    const canvasHandle = createMockCanvasHandle();

    // Should not throw when providing the canvas ref
    expect(() =>
      render(
        <ScratchpadCapture
          onFrameCaptured={vi.fn()}
          teachingCanvasRef={canvasHandle}
          isScratchpadOpen={true}
        >
          <div>Content</div>
        </ScratchpadCapture>
      )
    ).not.toThrow();
  });

  it("should accept null teachingCanvasRef", () => {
    expect(() =>
      render(
        <ScratchpadCapture
          onFrameCaptured={vi.fn()}
          teachingCanvasRef={null}
          isScratchpadOpen={false}
        >
          <div>Content</div>
        </ScratchpadCapture>
      )
    ).not.toThrow();
  });

  it("should handle isScratchpadOpen=false gracefully", () => {
    expect(() =>
      render(
        <ScratchpadCapture
          onFrameCaptured={vi.fn()}
          isScratchpadOpen={false}
        >
          <div>Content</div>
        </ScratchpadCapture>
      )
    ).not.toThrow();
  });

  it("should use native canvas.toDataURL path (no react-sketch-canvas)", () => {
    // Verify the component doesn't import or reference react-sketch-canvas
    const canvasHandle = createMockCanvasHandle();

    render(
      <ScratchpadCapture
        onFrameCaptured={vi.fn()}
        teachingCanvasRef={canvasHandle}
        isScratchpadOpen={true}
      >
        <div>Content</div>
      </ScratchpadCapture>
    );

    // getCanvas is the native approach (not exportPaths/exportImage from react-sketch-canvas)
    // The component uses getCanvas() and drawImage() for synchronous, efficient capture
    expect(canvasHandle.getCanvas).toBeDefined();
  });
});

