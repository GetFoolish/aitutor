import React, { useRef, useImperativeHandle, forwardRef, useEffect, useState } from 'react';
import CanvasDraw from 'react-canvas-draw';
import { Button } from "@/components/ui/button";
import { Trash2 } from 'lucide-react';

export interface ScratchpadRef {
  getCanvas: () => HTMLCanvasElement | null;
  clear: () => void;
}

interface ScratchpadProps {}

const Scratchpad = forwardRef<ScratchpadRef, ScratchpadProps>((props, ref) => {
  const canvasDrawRef = useRef<CanvasDraw>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasWrapperRef = useRef<HTMLDivElement>(null);
  const [brushColor, setBrushColor] = useState('#000000');
  const [brushRadius, setBrushRadius] = useState(3);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });

  // Calculate canvas dimensions based on container size
  useEffect(() => {
    const updateCanvasSize = () => {
      if (canvasWrapperRef.current) {
        const rect = canvasWrapperRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          setCanvasSize({
            width: Math.floor(rect.width),
            height: Math.floor(rect.height)
          });
        }
      }
    };

    // Wait for next frame to ensure DOM is ready
    const timeoutId = setTimeout(() => {
      updateCanvasSize();
    }, 0);

    // Also use requestAnimationFrame for immediate update
    requestAnimationFrame(() => {
      updateCanvasSize();
    });

    // Update on window resize
    const handleResize = () => {
      requestAnimationFrame(updateCanvasSize);
    };
    window.addEventListener('resize', handleResize);
    
    // Use ResizeObserver for more accurate size tracking
    let resizeObserver: ResizeObserver | null = null;
    if (canvasWrapperRef.current && window.ResizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(updateCanvasSize);
      });
      resizeObserver.observe(canvasWrapperRef.current);
    }

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('resize', handleResize);
      if (resizeObserver && canvasWrapperRef.current) {
        resizeObserver.unobserve(canvasWrapperRef.current);
      }
    };
  }, []);

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    getCanvas: () => {
      // Find the canvas element within our container
      if (containerRef.current) {
        const canvas = containerRef.current.querySelector('canvas');
        if (canvas) {
          return canvas;
        }
      }
      // Fallback: try to find via react-canvas-draw ref
      if (canvasDrawRef.current) {
        const canvasDrawInstance = canvasDrawRef.current as any;
        if (canvasDrawInstance.canvas) {
          return canvasDrawInstance.canvas;
        }
      }
      return null;
    },
    clear: () => {
      canvasDrawRef.current?.clear();
    }
  }));

  return (
    <div ref={containerRef} className="relative h-full w-full bg-white border-[4px] border-black overflow-hidden">
      {/* Toolbar */}
      <div className="absolute top-2 left-2 right-2 z-50 flex items-center gap-2 p-2 bg-[#FFD93D] border-[3px] border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
        <div className="flex items-center gap-2">
          <label className="text-xs font-black uppercase text-black whitespace-nowrap">Color:</label>
          <input
            type="color"
            value={brushColor}
            onChange={(e) => setBrushColor(e.target.value)}
            className="w-8 h-8 border-[2px] border-black cursor-pointer"
            title="Brush Color"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-black uppercase text-black whitespace-nowrap">Size:</label>
          <input
            type="range"
            min="1"
            max="20"
            value={brushRadius}
            onChange={(e) => setBrushRadius(Number(e.target.value))}
            className="w-20"
            title="Brush Size"
          />
          <span className="text-xs font-black text-black w-6 text-center">{brushRadius}</span>
        </div>
        <div className="flex-1" />
        <Button
          onClick={() => canvasDrawRef.current?.clear()}
          className="h-8 px-3 text-xs font-black uppercase border-[2px] border-black bg-[#FF6B6B] text-white hover:bg-[#FF5252] hover:opacity-90 shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
          type="button"
        >
          <Trash2 className="w-3 h-3 mr-1" />
          Clear
        </Button>
      </div>

      {/* Canvas */}
      <div ref={canvasWrapperRef} className="h-full w-full pt-14">
        {canvasSize.width > 0 && canvasSize.height > 0 && (
          <CanvasDraw
            ref={canvasDrawRef}
            brushColor={brushColor}
            brushRadius={brushRadius}
            canvasWidth={canvasSize.width}
            canvasHeight={canvasSize.height}
            hideGrid={false}
            gridColor="#e0e0e0"
            gridSizeX={20}
            gridSizeY={20}
            lazyRadius={0}
            catenaryColor="#0a0302"
            backgroundColor="#FFFFFF"
            immediateLoading={true}
            loadTimeOffset={0}
          />
        )}
      </div>
    </div>
  );
});

Scratchpad.displayName = 'Scratchpad';

export default Scratchpad;
