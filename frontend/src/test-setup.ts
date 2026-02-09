import "@testing-library/jest-dom";

// Mock requestAnimationFrame for tests
if (typeof globalThis.requestAnimationFrame === "undefined") {
  globalThis.requestAnimationFrame = (cb: FrameRequestCallback): number => {
    return setTimeout(() => cb(performance.now()), 0) as unknown as number;
  };
  globalThis.cancelAnimationFrame = (id: number) => {
    clearTimeout(id);
  };
}

// Mock canvas context for jsdom (which doesn't support canvas)
HTMLCanvasElement.prototype.getContext = function (
  contextId: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _options?: any
) {
  if (contextId === "2d") {
    return {
      fillStyle: "",
      strokeStyle: "",
      lineWidth: 1,
      lineCap: "butt",
      lineJoin: "miter",
      font: "10px sans-serif",
      textBaseline: "alphabetic",
      textAlign: "start",
      globalCompositeOperation: "source-over",
      fillRect: vi.fn(),
      clearRect: vi.fn(),
      strokeRect: vi.fn(),
      beginPath: vi.fn(),
      closePath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      arc: vi.fn(),
      stroke: vi.fn(),
      fill: vi.fn(),
      fillText: vi.fn(),
      measureText: vi.fn(() => ({ width: 0 })),
      save: vi.fn(),
      restore: vi.fn(),
      drawImage: vi.fn(),
      getImageData: vi.fn(() => ({
        data: new Uint8ClampedArray(0),
        width: 0,
        height: 0,
      })),
      putImageData: vi.fn(),
      setTransform: vi.fn(),
      resetTransform: vi.fn(),
      translate: vi.fn(),
      scale: vi.fn(),
      rotate: vi.fn(),
      canvas: this,
    } as unknown as CanvasRenderingContext2D;
  }
  return null;
} as any;

HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/png;base64,test");

