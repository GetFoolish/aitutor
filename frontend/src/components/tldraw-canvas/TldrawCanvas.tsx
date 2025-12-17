import React, { useState, useImperativeHandle, forwardRef, useCallback, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Tldraw, Editor, TLUiOverrides, TLComponents } from 'tldraw';
import 'tldraw/tldraw.css';
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { X, Trash2 } from 'lucide-react';
import cn from 'classnames';

export interface TldrawCanvasRef {
  getCanvas: () => HTMLCanvasElement | null;
  clear: () => void;
  exportCanvas: () => Promise<HTMLCanvasElement | null>;
}

interface TldrawCanvasProps {
  onClose?: () => void;
}

const TldrawCanvas = forwardRef<TldrawCanvasRef, TldrawCanvasProps>((props, ref) => {
  const [editor, setEditor] = useState<Editor | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [canvasOpacity, setCanvasOpacity] = useState(0.95); // Control canvas opacity

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

  // Export canvas as HTMLCanvasElement for MediaMixer
  const exportCanvas = useCallback(async (): Promise<HTMLCanvasElement | null> => {
    if (!editor) {
      console.warn('Editor not ready for export');
      return null;
    }

    try {
      // Get all shapes on the canvas
      const shapeIds = editor.getCurrentPageShapeIds();
      
      if (shapeIds.size === 0) {
        // Canvas is empty, return blank white canvas
        const canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 720;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, 1280, 720);
        }
        canvasRef.current = canvas;
        return canvas;
      }

      // Export the canvas to blob using editor.toImage (tldraw v4 API)
      // toImage requires shape IDs as first parameter
      const result = await editor.toImage(Array.from(shapeIds), {
        format: 'png',
        quality: 1,
        background: true,
        scale: 1,
      });

      if (!result || !result.blob) {
        console.warn('❌ Failed to export tldraw canvas');
        return null;
      }
      
      const blob = result.blob;
      console.log('✅ Tldraw canvas exported successfully, blob size:', blob.size);

      // Convert blob to canvas
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
          console.error('❌ Failed to load image from blob');
          resolve(null);
        };
        img.src = URL.createObjectURL(blob);
      });
    } catch (error) {
      console.error('❌ Error exporting tldraw canvas:', error);
      return null;
    }
  }, [editor]);

  // Clear canvas
  const clearCanvas = useCallback(() => {
    if (editor) {
      editor.selectAll();
      editor.deleteShapes(editor.getSelectedShapeIds());
      editor.resetZoom();
    }
  }, [editor]);

  // Handle opacity slider change
  const handleOpacityChange = useCallback((value: number[]) => {
    setCanvasOpacity(value[0] / 100); // Convert 0-100 to 0-1
  }, []);

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    getCanvas: () => canvasRef.current,
    clear: clearCanvas,
    exportCanvas: exportCanvas
  }));

  // Hide unwanted UI components
  const components: Partial<TLComponents> = {
    PageMenu: null, // Hide pagination
    MainMenu: null, // Hide file/export menu
  };

  // Custom UI overrides to match your theme
  const uiOverrides: TLUiOverrides = {
    tools(editor, tools) {
      return tools;
    },
  };

  // Render canvas using Portal to bypass stacking context issues
  return createPortal(
    <div 
      className="fixed left-0 right-0 bottom-0 flex flex-col top-[44px] lg:top-[48px]"
      style={{ zIndex: 999 }}
    >
      {/* Top Toolbar - Fixed at top */}
      <div 
        className={cn(
          "flex items-center justify-between p-2 md:p-3 border-b-[3px] lg:border-b-[4px] border-black dark:border-white",
          "bg-[#FFD93D]"
        )}
        style={{
          opacity: canvasOpacity,
          zIndex: 1000
        }}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 border-[3px] border-black dark:border-white bg-white dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
            <span className="text-lg">✏️</span>
          </div>
          <div>
            <h2 className="text-base font-black uppercase text-black">Canvas Mode</h2>
            <p className="text-[10px] font-bold text-black/70">Draw, write, add shapes & text - Question visible below</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Opacity Slider */}
          <div className="flex items-center gap-2 px-3 py-2 border-[3px] border-black bg-white dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
            <span className="text-xs font-black text-black dark:text-white whitespace-nowrap">Opacity:</span>
            <Slider
              value={[canvasOpacity * 100]}
              onValueChange={handleOpacityChange}
              min={50}
              max={100}
              step={5}
              className="w-24"
            />
            <span className="text-xs font-bold text-black dark:text-white w-8">{Math.round(canvasOpacity * 100)}%</span>
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

      {/* Full Screen Canvas Overlay with Transparency */}
      <div 
        className="flex-1 relative"
        style={{
          opacity: canvasOpacity,
          transition: 'opacity 0.3s ease',
          zIndex: 999
        }}
      >
        <Tldraw
          onMount={setEditor}
          overrides={uiOverrides}
          components={components}
          inferDarkMode={false}
          forceMobile={false}
        />
      </div>

      {/* Bottom Info Bar - Fixed at bottom */}
      <div 
        className={cn(
          "p-2 border-t-[3px] border-black dark:border-white",
          "bg-[#4ADE80]"
        )}
        style={{
          opacity: canvasOpacity,
          zIndex: 1000
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

TldrawCanvas.displayName = 'TldrawCanvas';

export default TldrawCanvas;

