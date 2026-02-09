import React, { useRef, useState, useEffect } from "react";
import { TeachingCanvas, TeachingCanvasHandle } from "../teaching-canvas";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface ScratchpadProps {
  onCanvasReady?: (canvasRef: TeachingCanvasHandle) => void;
}

// Global reference for TutorDrawingHandler and frame capture
declare global {
  interface Window {
    __teachingCanvasRef?: TeachingCanvasHandle | null;
  }
}

const COLORS = [
  "#1e1e1e", // black
  "#e03131", // red
  "#2f9e44", // green
  "#1971c2", // blue
  "#f08c00", // orange
  "#9c36b5", // purple
];

const STROKE_WIDTHS = [2, 4, 8, 12];

const Scratchpad = ({ onCanvasReady }: ScratchpadProps) => {
  const canvasRef = useRef<TeachingCanvasHandle>(null);
  const [strokeColor, setStrokeColor] = useState("#1e1e1e");
  const [strokeWidth, setStrokeWidth] = useState(4);
  const [isEraser, setIsEraser] = useState(false);

  const handleClearAll = () => {
    canvasRef.current?.clear();
  };

  const handleUndo = () => {
    canvasRef.current?.undo();
  };

  const handleRedo = () => {
    canvasRef.current?.redo();
  };

  const toggleEraser = () => {
    if (isEraser) {
      canvasRef.current?.setEraserMode(false);
      setIsEraser(false);
    } else {
      canvasRef.current?.setEraserMode(true);
      setIsEraser(true);
    }
  };

  // Store ref globally when canvas is ready
  useEffect(() => {
    if (canvasRef.current) {
      window.__teachingCanvasRef = canvasRef.current;
      onCanvasReady?.(canvasRef.current);
    }
    return () => {
      window.__teachingCanvasRef = null;
    };
  }, [onCanvasReady]);

  return (
    <div style={{
      position: 'relative',
      height: '100%',
      width: '100%',
      background: '#fff',
      borderRadius: '8px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        borderBottom: '1px solid #e5e5e5',
        background: '#fafafa',
        flexWrap: 'wrap'
      }}>
        {/* Colors */}
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {COLORS.map((color) => (
            <button
              key={color}
              onClick={() => {
                setStrokeColor(color);
                setIsEraser(false);
                canvasRef.current?.setStrokeColor(color);
              }}
              style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: color,
                border: strokeColor === color && !isEraser ? '3px solid #000' : '2px solid #ccc',
                cursor: 'pointer',
                padding: 0
              }}
              title={color}
            />
          ))}
        </div>

        <div style={{ width: 1, height: 24, background: '#ddd' }} />

        {/* Stroke widths */}
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {STROKE_WIDTHS.map((width) => (
            <button
              key={width}
              onClick={() => {
                setStrokeWidth(width);
                canvasRef.current?.setStrokeWidth(width);
              }}
              style={{
                width: 28,
                height: 28,
                borderRadius: '4px',
                background: strokeWidth === width ? '#e5e5e5' : 'transparent',
                border: '1px solid #ccc',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title={`${width}px`}
            >
              <div style={{
                width: width + 4,
                height: width + 4,
                borderRadius: '50%',
                background: '#333'
              }} />
            </button>
          ))}
        </div>

        <div style={{ width: 1, height: 24, background: '#ddd' }} />

        {/* Eraser */}
        <Button
          type="button"
          size="sm"
          variant={isEraser ? "default" : "outline"}
          onClick={toggleEraser}
          style={{ height: 28 }}
        >
          <span className="material-symbols-outlined text-sm">ink_eraser</span>
        </Button>

        {/* Undo/Redo */}
        <Button type="button" size="sm" variant="outline" onClick={handleUndo} style={{ height: 28 }}>
          <span className="material-symbols-outlined text-sm">undo</span>
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={handleRedo} style={{ height: 28 }}>
          <span className="material-symbols-outlined text-sm">redo</span>
        </Button>

        <div style={{ flex: 1 }} />

        {/* Clear All */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button type="button" size="sm" variant="destructive" style={{ height: 28 }}>
              Clear Board
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear entire whiteboard?</AlertDialogTitle>
              <AlertDialogDescription>
                This will delete all your drawings. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleClearAll}>Clear All</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Canvas */}
      <div style={{ flex: 1, position: 'relative' }}>
        <TeachingCanvas
          ref={canvasRef}
          width={800}
          height={600}
          backgroundColor="#ffffff"
        />
      </div>
    </div>
  );
};

export default Scratchpad;
