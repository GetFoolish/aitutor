import React, { useState, useImperativeHandle, forwardRef, useCallback, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Canvas, PencilBrush, Rect, Circle as FabricCircle, IText, Object as FabricObject } from 'fabric';
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { X, Trash2, Pencil, Square, Circle, Type, Eraser } from 'lucide-react';
import cn from 'classnames';

export interface FabricCanvasRef {
  getCanvas: () => HTMLCanvasElement | null;
  clear: () => void;
  exportCanvas: () => Promise<HTMLCanvasElement | null>;
}

interface FabricCanvasProps {
  onClose?: () => void;
}

type DrawingTool = 'pen' | 'rectangle' | 'circle' | 'text' | 'eraser';

const FabricCanvas = forwardRef<FabricCanvasRef, FabricCanvasProps>((props, ref) => {
  const [fabricCanvas, setFabricCanvas] = useState<Canvas | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [canvasOpacity, setCanvasOpacity] = useState(0.95);
  const [selectedTool, setSelectedTool] = useState<DrawingTool>('pen');
  const [brushColor, setBrushColor] = useState('#000000');
  const [brushSize, setBrushSize] = useState(2);

  // Detect dark mode
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(document.documentElement.classList.contains('dark'));
    };
    checkDarkMode();

    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Initialize Fabric.js canvas
  useEffect(() => {
    if (!canvasRef.current || fabricCanvas) return;

    const canvas = new Canvas(canvasRef.current, {
      isDrawingMode: true,
      width: window.innerWidth,
      height: window.innerHeight - 150, // Account for toolbars
      backgroundColor: '#ffffff',
    });

    // Set initial brush
    canvas.freeDrawingBrush = new PencilBrush(canvas);
    canvas.freeDrawingBrush.color = brushColor;
    canvas.freeDrawingBrush.width = brushSize;

    setFabricCanvas(canvas);

    // Handle window resize
    const handleResize = () => {
      if (canvas) {
        canvas.setDimensions({
          width: window.innerWidth,
          height: window.innerHeight - 150,
        });
        canvas.renderAll();
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      canvas.dispose();
    };
  }, []);

  // Update tool when selected
  useEffect(() => {
    if (!fabricCanvas) return;

    switch (selectedTool) {
      case 'pen':
        fabricCanvas.isDrawingMode = true;
        fabricCanvas.freeDrawingBrush = new PencilBrush(fabricCanvas);
        fabricCanvas.freeDrawingBrush.color = brushColor;
        fabricCanvas.freeDrawingBrush.width = brushSize;
        break;

      case 'eraser':
        fabricCanvas.isDrawingMode = true;
        const eraserBrush = new PencilBrush(fabricCanvas);
        eraserBrush.color = '#ffffff'; // White for erasing
        eraserBrush.width = brushSize * 3;
        fabricCanvas.freeDrawingBrush = eraserBrush;
        break;

      case 'rectangle':
      case 'circle':
      case 'text':
        fabricCanvas.isDrawingMode = false;
        break;
    }
  }, [selectedTool, fabricCanvas, brushColor, brushSize]);

  // Update brush color and size
  useEffect(() => {
    if (!fabricCanvas || !fabricCanvas.freeDrawingBrush) return;
    if (selectedTool === 'pen') {
      fabricCanvas.freeDrawingBrush.color = brushColor;
      fabricCanvas.freeDrawingBrush.width = brushSize;
    }
  }, [brushColor, brushSize, fabricCanvas, selectedTool]);

  // Handle shape drawing
  useEffect(() => {
    if (!fabricCanvas) return;

    let isDrawing = false;
    let startX = 0;
    let startY = 0;
    let shape: FabricObject | null = null;

    const handleMouseDown = (e: any) => {
      if (selectedTool === 'rectangle' || selectedTool === 'circle') {
        isDrawing = true;
        const pointer = fabricCanvas.getPointer(e.e);
        startX = pointer.x;
        startY = pointer.y;

        if (selectedTool === 'rectangle') {
          shape = new Rect({
            left: startX,
            top: startY,
            width: 0,
            height: 0,
            fill: 'transparent',
            stroke: brushColor,
            strokeWidth: brushSize,
          });
        } else if (selectedTool === 'circle') {
          shape = new FabricCircle({
            left: startX,
            top: startY,
            radius: 0,
            fill: 'transparent',
            stroke: brushColor,
            strokeWidth: brushSize,
          });
        }

        if (shape) {
          fabricCanvas.add(shape);
        }
      } else if (selectedTool === 'text') {
        const pointer = fabricCanvas.getPointer(e.e);
        const text = new IText('Type here...', {
          left: pointer.x,
          top: pointer.y,
          fill: brushColor,
          fontSize: brushSize * 10,
          fontFamily: 'Arial',
        });
        fabricCanvas.add(text);
        fabricCanvas.setActiveObject(text);
        text.enterEditing();
      }
    };

    const handleMouseMove = (e: any) => {
      if (!isDrawing || !shape) return;

      const pointer = fabricCanvas.getPointer(e.e);

      if (selectedTool === 'rectangle' && shape instanceof Rect) {
        const width = pointer.x - startX;
        const height = pointer.y - startY;
        shape.set({ width: Math.abs(width), height: Math.abs(height) });
        if (width < 0) shape.set({ left: pointer.x });
        if (height < 0) shape.set({ top: pointer.y });
      } else if (selectedTool === 'circle' && shape instanceof FabricCircle) {
        const radius = Math.sqrt(
          Math.pow(pointer.x - startX, 2) + Math.pow(pointer.y - startY, 2)
        );
        shape.set({ radius: radius / 2 });
      }

      fabricCanvas.renderAll();
    };

    const handleMouseUp = () => {
      isDrawing = false;
      shape = null;
    };

    if (selectedTool === 'rectangle' || selectedTool === 'circle' || selectedTool === 'text') {
      fabricCanvas.on('mouse:down', handleMouseDown);
      fabricCanvas.on('mouse:move', handleMouseMove);
      fabricCanvas.on('mouse:up', handleMouseUp);
    }

    return () => {
      fabricCanvas.off('mouse:down', handleMouseDown);
      fabricCanvas.off('mouse:move', handleMouseMove);
      fabricCanvas.off('mouse:up', handleMouseUp);
    };
  }, [fabricCanvas, selectedTool, brushColor, brushSize]);

  // Export canvas as HTMLCanvasElement
  const exportCanvas = useCallback(async (): Promise<HTMLCanvasElement | null> => {
    if (!fabricCanvas) {
      console.warn('Canvas not ready for export');
      return null;
    }

    try {
      // Export to data URL
      const dataURL = fabricCanvas.toDataURL({
        format: 'png',
        quality: 1,
        multiplier: 1,
      });

      // Convert to canvas
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = 1280;
          canvas.height = 720;
          const ctx = canvas.getContext('2d');

          if (ctx) {
            // Fill with white background
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, 1280, 720);

            // Calculate aspect ratio fit
            const scale = Math.min(1280 / img.width, 720 / img.height);
            const x = (1280 - img.width * scale) / 2;
            const y = (720 - img.height * scale) / 2;

            ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
          }

          canvasRef.current = canvas;
          console.log('✅ Canvas converted and ready for Adam:', canvas.width, 'x', canvas.height);
          resolve(canvas);
        };
        img.onerror = () => {
          console.error('❌ Failed to load image');
          resolve(null);
        };
        img.src = dataURL;
      });
    } catch (error) {
      console.error('❌ Error exporting canvas:', error);
      return null;
    }
  }, [fabricCanvas]);

  // Clear canvas
  const clearCanvas = useCallback(() => {
    if (fabricCanvas) {
      fabricCanvas.clear();
      fabricCanvas.backgroundColor = '#ffffff';
      fabricCanvas.renderAll();
    }
  }, [fabricCanvas]);

  // Handle opacity slider change
  const handleOpacityChange = useCallback((value: number[]) => {
    setCanvasOpacity(value[0] / 100);
  }, []);

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    getCanvas: () => canvasRef.current,
    clear: clearCanvas,
    exportCanvas: exportCanvas,
  }));

  const toolButtons = [
    { tool: 'pen' as DrawingTool, icon: Pencil, label: 'Pen' },
    { tool: 'rectangle' as DrawingTool, icon: Square, label: 'Rectangle' },
    { tool: 'circle' as DrawingTool, icon: Circle, label: 'Circle' },
    { tool: 'text' as DrawingTool, icon: Type, label: 'Text' },
    { tool: 'eraser' as DrawingTool, icon: Eraser, label: 'Eraser' },
  ];

  return createPortal(
    <div
      ref={containerRef}
      className="fixed left-0 right-0 bottom-0 flex flex-col top-[44px] lg:top-[48px]"
      style={{ zIndex: 999 }}
    >
      {/* Top Toolbar */}
      <div
        className={cn(
          "flex items-center justify-between p-2 md:p-3 border-b-[3px] lg:border-b-[4px] border-black dark:border-white",
          "bg-[#FFD93D]"
        )}
        style={{
          opacity: canvasOpacity,
          zIndex: 1000,
        }}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 border-[3px] border-black dark:border-white bg-white dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
            <span className="text-lg">✏️</span>
          </div>
          <div>
            <h2 className="text-base font-black uppercase text-black">Canvas Mode</h2>
            <p className="text-[10px] font-bold text-black/70">
              Draw, write, add shapes & text - Question visible below
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Opacity Slider */}
          <div className="flex items-center gap-2 px-3 py-2 border-[3px] border-black bg-white dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
            <span className="text-xs font-black text-black dark:text-white whitespace-nowrap">
              Opacity:
            </span>
            <Slider
              value={[canvasOpacity * 100]}
              onValueChange={handleOpacityChange}
              min={50}
              max={100}
              step={5}
              className="w-24"
            />
            <span className="text-xs font-bold text-black dark:text-white w-8">
              {Math.round(canvasOpacity * 100)}%
            </span>
          </div>

          <Button
            onClick={clearCanvas}
            className={cn(
              "h-9 px-4 text-xs font-black uppercase transition-all",
              "border-[3px] border-black bg-[#FF6B6B] text-white",
              "hover:bg-[#FF5252] hover:translate-x-0.5 hover:translate-y-0.5",
              "shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none"
            )}
            type="button"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            Clear
          </Button>

          <Button
            onClick={props.onClose}
            className={cn(
              "h-9 w-9 p-0 transition-all",
              "border-[3px] border-black dark:border-white",
              "bg-white dark:bg-[#000000] text-black dark:text-white",
              "hover:bg-[#FF6B6B] hover:text-white",
              "hover:translate-x-0.5 hover:translate-y-0.5",
              "shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none"
            )}
            type="button"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Canvas Area */}
      <div
        className="flex-1 relative"
        style={{
          opacity: canvasOpacity,
          transition: 'opacity 0.3s ease',
          zIndex: 999,
        }}
      >
        {/* Drawing Tools */}
        <div
          className="absolute left-4 top-4 flex flex-col gap-2 p-2 bg-[#FFD93D] border-[3px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
          style={{ zIndex: 1001 }}
        >
          {toolButtons.map(({ tool, icon: Icon, label }) => (
            <button
              key={tool}
              onClick={() => setSelectedTool(tool)}
              className={cn(
                "w-10 h-10 flex items-center justify-center transition-all",
                "border-[2px] border-black",
                selectedTool === tool
                  ? "bg-[#4ADE80] text-black"
                  : "bg-white text-black hover:bg-[#C4B5FD]",
                "shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none",
                "hover:translate-x-0.5 hover:translate-y-0.5"
              )}
              title={label}
            >
              <Icon className="w-5 h-5" />
            </button>
          ))}

          {/* Color Picker */}
          <div className="w-10 h-10 border-[2px] border-black bg-white p-1">
            <input
              type="color"
              value={brushColor}
              onChange={(e) => setBrushColor(e.target.value)}
              className="w-full h-full cursor-pointer border-none"
              title="Color"
            />
          </div>

          {/* Brush Size */}
          <div className="w-10 flex flex-col items-center gap-1 py-2 border-[2px] border-black bg-white">
            <input
              type="range"
              min="1"
              max="20"
              value={brushSize}
              onChange={(e) => setBrushSize(Number(e.target.value))}
              className="w-8"
              style={{ WebkitAppearance: 'slider-vertical' } as React.CSSProperties}
              title="Brush Size"
            />
            <span className="text-[8px] font-black">{brushSize}</span>
          </div>
        </div>

        {/* Fabric Canvas */}
        <canvas ref={canvasRef} />
      </div>

      {/* Bottom Info Bar */}
      <div
        className={cn(
          "p-2 border-t-[3px] border-black dark:border-white",
          "bg-[#4ADE80]"
        )}
        style={{
          opacity: canvasOpacity,
          zIndex: 1000,
        }}
      >
        <p className="text-xs font-black text-center text-black flex items-center justify-center gap-2">
          <span className="inline-block w-2 h-2 bg-black rounded-full animate-pulse"></span>
          Adam can see your canvas in real-time
          <span className="text-black/70">•</span>
          Question visible in background
        </p>
      </div>
    </div>,
    document.body
  );
});

FabricCanvas.displayName = 'FabricCanvas';

export default FabricCanvas;

