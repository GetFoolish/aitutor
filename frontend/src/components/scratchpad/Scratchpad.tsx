import React, {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  useEffect,
} from "react";
import { ReactSketchCanvas } from "react-sketch-canvas";
import { captureCanvasAsBase64, drawOnScratchpad, ExternalStroke } from "@/utils/canvas";

export type ScratchpadHandle = {
  /** Capture the canvas as a base64-encoded PNG. Returns null if not available. */
  capture: () => Promise<string | null>;

  /**
   * Programmatically draw strokes on the canvas.
   * Each stroke will be sanitized to include `drawMode: true`.
   */
  drawExternal: (strokes: ExternalStroke[]) => Promise<void>;
};

const Scratchpad = forwardRef<ScratchpadHandle, {}>((_props, ref) => {
  const canvasRef = useRef<any>(null);
  const [color, setColor] = useState<string>("#000000");
  const [strokeWidth, setStrokeWidth] = useState<number>(4);
  const [isEraser, setIsEraser] = useState<boolean>(false);

  useImperativeHandle(ref, () => ({
    /**
     * Capture the canvas as a base64-encoded PNG.
     * Returns `null` if the canvas is not ready.
     */
    capture: async () => {
      return await captureCanvasAsBase64(canvasRef);
    },

    /**
     * Draw an array of external strokes onto the canvas. Each stroke will be
     * sanitized to ensure `drawMode: true`.
     */
    drawExternal: async (strokes: ExternalStroke[] = []) => {
      const sanitized = (strokes || []).map((s) => ({ ...s, drawMode: true }));
      await drawOnScratchpad(canvasRef, sanitized);
    },
  }));

  // Expose simple global handle for other parts of the app
  useEffect(() => {
    (window as any).__scratchpadHandle = {
      capture: async () => await captureCanvasAsBase64(canvasRef),
      drawExternal: async (strokes: ExternalStroke[] = []) => {
        const sanitized = (strokes || []).map((s) => ({ ...s, drawMode: true }));
        await drawOnScratchpad(canvasRef, sanitized);
      },
    } as ScratchpadHandle;
    return () => {
      try {
        delete (window as any).__scratchpadHandle;
      } catch (e) {}
    };
  }, []);

  const handleUndo = () => {
    canvasRef.current?.undo();
  };
  const handleRedo = () => {
    canvasRef.current?.redo();
  };
  const handleClear = () => {
    canvasRef.current?.clearCanvas();
  };
  const toggleEraser = () => {
    const next = !isEraser;
    setIsEraser(next);
    // react-sketch-canvas supports eraseMode
    if (typeof canvasRef.current?.eraseMode === "function") {
      canvasRef.current.eraseMode(next);
    }
    // If erase mode not supported, set color to background as a fallback
    if (!canvasRef.current?.eraseMode) {
      setColor(next ? "#ffffff" : "#000000");
    }
  };

  return (
    <div className="w-full h-full flex-grow relative rounded-md bg-white shadow-sm">
      <div className="absolute left-3 top-3 z-20 flex items-center gap-2 bg-white/80 p-2 rounded-md shadow-sm">
        <label className="flex items-center gap-1 text-xs">
          <span className="text-gray-600">Color</span>
          <input
            aria-label="Stroke color"
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="w-8 h-8 p-0 border-0"
          />
        </label>
        <label className="flex items-center gap-1 text-xs">
          <span className="text-gray-600">Width</span>
          <input
            aria-label="Stroke width"
            type="range"
            min={1}
            max={40}
            value={strokeWidth}
            onChange={(e) => setStrokeWidth(Number(e.target.value))}
            className="w-28"
          />
        </label>
        <button
          onClick={toggleEraser}
          className="px-2 py-1 text-sm bg-gray-100 rounded-md hover:bg-gray-200"
        >
          {isEraser ? "Eraser On" : "Eraser"}
        </button>
        <button
          onClick={handleUndo}
          className="px-2 py-1 text-sm bg-gray-100 rounded-md hover:bg-gray-200"
        >
          Undo
        </button>
        <button
          onClick={handleRedo}
          className="px-2 py-1 text-sm bg-gray-100 rounded-md hover:bg-gray-200"
        >
          Redo
        </button>
        <button
          onClick={handleClear}
          className="px-2 py-1 text-sm bg-red-100 text-red-700 rounded-md hover:bg-red-200"
        >
          Clear
        </button>
      </div>

      <div className="absolute inset-0">
        <ReactSketchCanvas
          ref={canvasRef}
          strokeWidth={strokeWidth}
          strokeColor={color}
          width="100%"
          height="100%"
          style={{ borderRadius: 6 }}
          canvasColor="#ffffff"
        />
      </div>
    </div>
  );
});

export default Scratchpad;
