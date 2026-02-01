/**
 * ScratchpadContext - Shares Excalidraw API for AI teacher drawing
 * 
 * Allows the AI tutor (Gemini) to draw on the scratchpad like a real teacher,
 * explaining concepts visually with diagrams, shapes, and annotations.
 */
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Excalidraw element types
interface ExcalidrawElement {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  strokeColor: string;
  backgroundColor: string;
  fillStyle: string;
  strokeWidth: number;
  roughness: number;
  opacity: number;
  [key: string]: any;
}

interface Point {
  x: number;
  y: number;
}

interface ScratchpadContextType {
  excalidrawAPI: any | null;
  setExcalidrawAPI: (api: any) => void;
  // Drawing functions for AI teacher
  drawLine: (startX: number, startY: number, endX: number, endY: number, color?: string, width?: number) => void;
  drawArrow: (startX: number, startY: number, endX: number, endY: number, color?: string) => void;
  drawRectangle: (x: number, y: number, width: number, height: number, color?: string, fill?: string) => void;
  drawCircle: (x: number, y: number, radius: number, color?: string, fill?: string) => void;
  drawText: (x: number, y: number, text: string, fontSize?: number, color?: string) => void;
  drawFreehand: (points: Point[], color?: string, width?: number) => void;
  clearCanvas: () => void;
  highlightArea: (x: number, y: number, width: number, height: number) => void;
  // Complex drawing for math/diagrams
  drawNumberLine: (x: number, y: number, start: number, end: number, highlight?: number) => void;
  drawFraction: (x: number, y: number, numerator: number, denominator: number) => void;
  drawGrid: (x: number, y: number, rows: number, cols: number, cellSize?: number) => void;
}

const ScratchpadContext = createContext<ScratchpadContextType | undefined>(undefined);

// Generate unique ID for Excalidraw elements
const generateId = () => Math.random().toString(36).substring(2, 15);

export const ScratchpadProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);

  // Helper to add elements to Excalidraw
  const addElements = useCallback((newElements: ExcalidrawElement[]) => {
    if (!excalidrawAPI) {
      console.warn('Excalidraw API not available');
      return;
    }
    
    const currentElements = excalidrawAPI.getSceneElements();
    excalidrawAPI.updateScene({
      elements: [...currentElements, ...newElements],
    });
  }, [excalidrawAPI]);

  // Draw a straight line
  const drawLine = useCallback((
    startX: number, 
    startY: number, 
    endX: number, 
    endY: number, 
    color: string = '#1e1e1e',
    width: number = 2
  ) => {
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'line',
      x: startX,
      y: startY,
      width: endX - startX,
      height: endY - startY,
      strokeColor: color,
      backgroundColor: 'transparent',
      fillStyle: 'hachure',
      strokeWidth: width,
      roughness: 1,
      opacity: 100,
      points: [[0, 0], [endX - startX, endY - startY]],
      lastCommittedPoint: null,
      startBinding: null,
      endBinding: null,
      startArrowhead: null,
      endArrowhead: null,
    };
    addElements([element]);
  }, [addElements]);

  // Draw an arrow
  const drawArrow = useCallback((
    startX: number, 
    startY: number, 
    endX: number, 
    endY: number, 
    color: string = '#1e1e1e'
  ) => {
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'arrow',
      x: startX,
      y: startY,
      width: endX - startX,
      height: endY - startY,
      strokeColor: color,
      backgroundColor: 'transparent',
      fillStyle: 'hachure',
      strokeWidth: 2,
      roughness: 1,
      opacity: 100,
      points: [[0, 0], [endX - startX, endY - startY]],
      lastCommittedPoint: null,
      startBinding: null,
      endBinding: null,
      startArrowhead: null,
      endArrowhead: 'arrow',
    };
    addElements([element]);
  }, [addElements]);

  // Draw a rectangle
  const drawRectangle = useCallback((
    x: number, 
    y: number, 
    width: number, 
    height: number, 
    color: string = '#1e1e1e',
    fill: string = 'transparent'
  ) => {
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'rectangle',
      x,
      y,
      width,
      height,
      strokeColor: color,
      backgroundColor: fill,
      fillStyle: fill === 'transparent' ? 'hachure' : 'solid',
      strokeWidth: 2,
      roughness: 1,
      opacity: 100,
    };
    addElements([element]);
  }, [addElements]);

  // Draw a circle (ellipse)
  const drawCircle = useCallback((
    x: number, 
    y: number, 
    radius: number, 
    color: string = '#1e1e1e',
    fill: string = 'transparent'
  ) => {
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'ellipse',
      x: x - radius,
      y: y - radius,
      width: radius * 2,
      height: radius * 2,
      strokeColor: color,
      backgroundColor: fill,
      fillStyle: fill === 'transparent' ? 'hachure' : 'solid',
      strokeWidth: 2,
      roughness: 1,
      opacity: 100,
    };
    addElements([element]);
  }, [addElements]);

  // Draw text
  const drawText = useCallback((
    x: number, 
    y: number, 
    text: string, 
    fontSize: number = 20,
    color: string = '#1e1e1e'
  ) => {
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'text',
      x,
      y,
      width: text.length * fontSize * 0.6,
      height: fontSize * 1.2,
      strokeColor: color,
      backgroundColor: 'transparent',
      fillStyle: 'hachure',
      strokeWidth: 1,
      roughness: 0,
      opacity: 100,
      text,
      fontSize,
      fontFamily: 1, // Virgil (hand-drawn style)
      textAlign: 'left',
      verticalAlign: 'top',
      baseline: fontSize,
      lineHeight: 1.25,
    };
    addElements([element]);
  }, [addElements]);

  // Draw freehand path
  const drawFreehand = useCallback((
    points: Point[], 
    color: string = '#1e1e1e',
    width: number = 2
  ) => {
    if (points.length < 2) return;
    
    const minX = Math.min(...points.map(p => p.x));
    const minY = Math.min(...points.map(p => p.y));
    const maxX = Math.max(...points.map(p => p.x));
    const maxY = Math.max(...points.map(p => p.y));
    
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'freedraw',
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
      strokeColor: color,
      backgroundColor: 'transparent',
      fillStyle: 'hachure',
      strokeWidth: width,
      roughness: 1,
      opacity: 100,
      points: points.map(p => [p.x - minX, p.y - minY]),
      pressures: points.map(() => 0.5),
      simulatePressure: true,
      lastCommittedPoint: points[points.length - 1],
    };
    addElements([element]);
  }, [addElements]);

  // Clear the canvas
  const clearCanvas = useCallback(() => {
    if (excalidrawAPI) {
      excalidrawAPI.resetScene();
    }
  }, [excalidrawAPI]);

  // Highlight an area (semi-transparent rectangle)
  const highlightArea = useCallback((
    x: number, 
    y: number, 
    width: number, 
    height: number
  ) => {
    const element: ExcalidrawElement = {
      id: generateId(),
      type: 'rectangle',
      x,
      y,
      width,
      height,
      strokeColor: '#ffeb3b',
      backgroundColor: '#fff9c4',
      fillStyle: 'solid',
      strokeWidth: 2,
      roughness: 0,
      opacity: 50,
    };
    addElements([element]);
  }, [addElements]);

  // Draw a number line (for math teaching)
  const drawNumberLine = useCallback((
    x: number, 
    y: number, 
    start: number, 
    end: number,
    highlight?: number
  ) => {
    const length = 400;
    const tickSpacing = length / (end - start);
    
    // Main line
    drawLine(x, y, x + length, y, '#1e1e1e', 2);
    
    // Ticks and numbers
    for (let i = start; i <= end; i++) {
      const tickX = x + (i - start) * tickSpacing;
      drawLine(tickX, y - 10, tickX, y + 10, '#1e1e1e', 1);
      drawText(tickX - 5, y + 15, String(i), 14, '#1e1e1e');
      
      // Highlight specific number
      if (highlight !== undefined && i === highlight) {
        drawCircle(tickX, y, 12, '#4caf50', '#c8e6c9');
      }
    }
    
    // Arrows at ends
    drawArrow(x - 20, y, x - 5, y, '#1e1e1e');
    drawArrow(x + length + 5, y, x + length + 20, y, '#1e1e1e');
  }, [drawLine, drawText, drawCircle, drawArrow]);

  // Draw a fraction visualization
  const drawFraction = useCallback((
    x: number, 
    y: number, 
    numerator: number, 
    denominator: number
  ) => {
    const width = 60;
    const height = 80;
    
    // Fraction bar
    drawLine(x, y, x + width, y, '#1e1e1e', 2);
    
    // Numerator
    drawText(x + width/2 - 10, y - 40, String(numerator), 28, '#1e1e1e');
    
    // Denominator
    drawText(x + width/2 - 10, y + 10, String(denominator), 28, '#1e1e1e');
  }, [drawLine, drawText]);

  // Draw a grid (for multiplication, area, etc.)
  const drawGrid = useCallback((
    x: number, 
    y: number, 
    rows: number, 
    cols: number,
    cellSize: number = 40
  ) => {
    // Horizontal lines
    for (let i = 0; i <= rows; i++) {
      drawLine(x, y + i * cellSize, x + cols * cellSize, y + i * cellSize, '#1e1e1e', 1);
    }
    
    // Vertical lines
    for (let j = 0; j <= cols; j++) {
      drawLine(x + j * cellSize, y, x + j * cellSize, y + rows * cellSize, '#1e1e1e', 1);
    }
  }, [drawLine]);

  const value: ScratchpadContextType = {
    excalidrawAPI,
    setExcalidrawAPI,
    drawLine,
    drawArrow,
    drawRectangle,
    drawCircle,
    drawText,
    drawFreehand,
    clearCanvas,
    highlightArea,
    drawNumberLine,
    drawFraction,
    drawGrid,
  };

  return (
    <ScratchpadContext.Provider value={value}>
      {children}
    </ScratchpadContext.Provider>
  );
};

export const useScratchpad = () => {
  const context = useContext(ScratchpadContext);
  if (context === undefined) {
    throw new Error('useScratchpad must be used within a ScratchpadProvider');
  }
  return context;
};

// Optional hook that doesn't throw if outside provider
export const useOptionalScratchpad = () => {
  return useContext(ScratchpadContext);
};

export default ScratchpadContext;
