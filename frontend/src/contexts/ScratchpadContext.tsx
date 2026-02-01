/**
 * ScratchpadContext - Exposes Excalidraw API for AI Teacher drawing
 * 
 * This context allows Gemini to draw on the whiteboard like a real teacher,
 * creating visual explanations, number lines, diagrams, and more.
 */
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Type for Excalidraw API - using any to avoid type import issues
type ExcalidrawImperativeAPI = any;

// Excalidraw element types
type ExcalidrawElement = {
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
  seed: number;
  version: number;
  versionNonce: number;
  isDeleted: boolean;
  groupIds: string[];
  boundElements: null | any[];
  updated: number;
  link: null | string;
  locked: boolean;
  [key: string]: any;
};

interface ScratchpadContextType {
  excalidrawAPI: ExcalidrawImperativeAPI | null;
  setExcalidrawAPI: (api: ExcalidrawImperativeAPI | null) => void;
  
  // Drawing functions for AI Teacher
  drawLine: (startX: number, startY: number, endX: number, endY: number, color?: string, width?: number) => void;
  drawArrow: (startX: number, startY: number, endX: number, endY: number, color?: string, width?: number) => void;
  drawRectangle: (x: number, y: number, width: number, height: number, color?: string, fill?: string) => void;
  drawCircle: (x: number, y: number, radius: number, color?: string, fill?: string) => void;
  drawText: (x: number, y: number, text: string, fontSize?: number, color?: string) => void;
  drawNumberLine: (startX: number, y: number, start: number, end: number, step?: number) => void;
  drawFraction: (x: number, y: number, numerator: number, denominator: number, fontSize?: number) => void;
  drawGrid: (x: number, y: number, rows: number, cols: number, cellSize?: number, color?: string) => void;
  highlightArea: (x: number, y: number, width: number, height: number) => void;
  clearCanvas: () => void;
}

const ScratchpadContext = createContext<ScratchpadContextType | null>(null);

// Helper to generate unique IDs
const generateId = () => Math.random().toString(36).substring(2, 15);

// Helper to create base element properties
const createBaseElement = (type: string, x: number, y: number, width: number, height: number, extras: Partial<ExcalidrawElement> = {}): ExcalidrawElement => ({
  id: generateId(),
  type,
  x,
  y,
  width,
  height,
  strokeColor: '#1e1e1e',
  backgroundColor: 'transparent',
  fillStyle: 'solid',
  strokeWidth: 2,
  roughness: 1,
  opacity: 100,
  seed: Math.floor(Math.random() * 100000),
  version: 1,
  versionNonce: Math.floor(Math.random() * 100000),
  isDeleted: false,
  groupIds: [],
  boundElements: null,
  updated: Date.now(),
  link: null,
  locked: false,
  ...extras,
});

export const ScratchpadProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);

  // Add element(s) to the canvas
  const addElements = useCallback((newElements: ExcalidrawElement[]) => {
    if (!excalidrawAPI) {
      console.warn('Excalidraw API not available');
      return;
    }
    const existingElements = excalidrawAPI.getSceneElements();
    excalidrawAPI.updateScene({
      elements: [...existingElements, ...newElements],
    });
  }, [excalidrawAPI]);

  // Draw a straight line
  const drawLine = useCallback((startX: number, startY: number, endX: number, endY: number, color = '#1e1e1e', width = 2) => {
    const element = createBaseElement('line', startX, startY, endX - startX, endY - startY, {
      strokeColor: color,
      strokeWidth: width,
      points: [[0, 0], [endX - startX, endY - startY]],
    });
    addElements([element]);
  }, [addElements]);

  // Draw an arrow
  const drawArrow = useCallback((startX: number, startY: number, endX: number, endY: number, color = '#1e1e1e', width = 2) => {
    const element = createBaseElement('arrow', startX, startY, endX - startX, endY - startY, {
      strokeColor: color,
      strokeWidth: width,
      points: [[0, 0], [endX - startX, endY - startY]],
      endArrowhead: 'arrow',
    });
    addElements([element]);
  }, [addElements]);

  // Draw a rectangle
  const drawRectangle = useCallback((x: number, y: number, width: number, height: number, color = '#1e1e1e', fill = 'transparent') => {
    const element = createBaseElement('rectangle', x, y, width, height, {
      strokeColor: color,
      backgroundColor: fill,
      fillStyle: fill !== 'transparent' ? 'solid' : 'hachure',
    });
    addElements([element]);
  }, [addElements]);

  // Draw a circle (ellipse)
  const drawCircle = useCallback((x: number, y: number, radius: number, color = '#1e1e1e', fill = 'transparent') => {
    const element = createBaseElement('ellipse', x - radius, y - radius, radius * 2, radius * 2, {
      strokeColor: color,
      backgroundColor: fill,
      fillStyle: fill !== 'transparent' ? 'solid' : 'hachure',
    });
    addElements([element]);
  }, [addElements]);

  // Draw text
  const drawText = useCallback((x: number, y: number, text: string, fontSize = 20, color = '#1e1e1e') => {
    const element = createBaseElement('text', x, y, text.length * fontSize * 0.6, fontSize * 1.2, {
      strokeColor: color,
      text,
      fontSize,
      fontFamily: 1, // Virgil (hand-drawn style)
      textAlign: 'left',
      verticalAlign: 'top',
      baseline: 'top',
    });
    addElements([element]);
  }, [addElements]);

  // Draw a number line - perfect for teaching addition/subtraction
  const drawNumberLine = useCallback((startX: number, y: number, start: number, end: number, step = 1) => {
    const elements: ExcalidrawElement[] = [];
    const totalNumbers = Math.floor((end - start) / step) + 1;
    const spacing = 50; // pixels between numbers
    const lineLength = (totalNumbers - 1) * spacing;

    // Main horizontal line
    elements.push(createBaseElement('line', startX, y, lineLength, 0, {
      strokeColor: '#1e1e1e',
      strokeWidth: 2,
      points: [[0, 0], [lineLength, 0]],
    }));

    // Arrow at the end
    elements.push(createBaseElement('arrow', startX + lineLength - 10, y, 20, 0, {
      strokeColor: '#1e1e1e',
      strokeWidth: 2,
      points: [[0, 0], [20, 0]],
      endArrowhead: 'arrow',
    }));

    // Tick marks and numbers
    for (let i = 0; i < totalNumbers; i++) {
      const x = startX + i * spacing;
      const num = start + i * step;

      // Tick mark
      elements.push(createBaseElement('line', x, y - 8, 0, 16, {
        strokeColor: '#1e1e1e',
        strokeWidth: 2,
        points: [[0, 0], [0, 16]],
      }));

      // Number label
      elements.push(createBaseElement('text', x - 5, y + 15, 10, 16, {
        strokeColor: '#1e1e1e',
        text: num.toString(),
        fontSize: 16,
        fontFamily: 1,
        textAlign: 'center',
        verticalAlign: 'top',
      }));
    }

    addElements(elements);
  }, [addElements]);

  // Draw a fraction
  const drawFraction = useCallback((x: number, y: number, numerator: number, denominator: number, fontSize = 24) => {
    const elements: ExcalidrawElement[] = [];
    const numStr = numerator.toString();
    const denStr = denominator.toString();
    const maxWidth = Math.max(numStr.length, denStr.length) * fontSize * 0.6;

    // Numerator
    elements.push(createBaseElement('text', x, y - fontSize - 5, maxWidth, fontSize, {
      strokeColor: '#1e1e1e',
      text: numStr,
      fontSize,
      fontFamily: 1,
      textAlign: 'center',
    }));

    // Fraction line
    elements.push(createBaseElement('line', x - 5, y, maxWidth + 10, 0, {
      strokeColor: '#1e1e1e',
      strokeWidth: 2,
      points: [[0, 0], [maxWidth + 10, 0]],
    }));

    // Denominator
    elements.push(createBaseElement('text', x, y + 5, maxWidth, fontSize, {
      strokeColor: '#1e1e1e',
      text: denStr,
      fontSize,
      fontFamily: 1,
      textAlign: 'center',
    }));

    addElements(elements);
  }, [addElements]);

  // Draw a grid - great for multiplication, area models
  const drawGrid = useCallback((x: number, y: number, rows: number, cols: number, cellSize = 40, color = '#1e1e1e') => {
    const elements: ExcalidrawElement[] = [];
    const width = cols * cellSize;
    const height = rows * cellSize;

    // Vertical lines
    for (let i = 0; i <= cols; i++) {
      elements.push(createBaseElement('line', x + i * cellSize, y, 0, height, {
        strokeColor: color,
        strokeWidth: 1,
        points: [[0, 0], [0, height]],
      }));
    }

    // Horizontal lines
    for (let i = 0; i <= rows; i++) {
      elements.push(createBaseElement('line', x, y + i * cellSize, width, 0, {
        strokeColor: color,
        strokeWidth: 1,
        points: [[0, 0], [width, 0]],
      }));
    }

    addElements(elements);
  }, [addElements]);

  // Highlight an area with yellow
  const highlightArea = useCallback((x: number, y: number, width: number, height: number) => {
    const element = createBaseElement('rectangle', x, y, width, height, {
      strokeColor: 'transparent',
      backgroundColor: '#fff3bf',
      fillStyle: 'solid',
      opacity: 50,
    });
    addElements([element]);
  }, [addElements]);

  // Clear the entire canvas
  const clearCanvas = useCallback(() => {
    if (excalidrawAPI) {
      excalidrawAPI.resetScene();
    }
  }, [excalidrawAPI]);

  return (
    <ScratchpadContext.Provider
      value={{
        excalidrawAPI,
        setExcalidrawAPI,
        drawLine,
        drawArrow,
        drawRectangle,
        drawCircle,
        drawText,
        drawNumberLine,
        drawFraction,
        drawGrid,
        highlightArea,
        clearCanvas,
      }}
    >
      {children}
    </ScratchpadContext.Provider>
  );
};

export const useScratchpad = () => {
  const context = useContext(ScratchpadContext);
  if (!context) {
    throw new Error('useScratchpad must be used within a ScratchpadProvider');
  }
  return context;
};
