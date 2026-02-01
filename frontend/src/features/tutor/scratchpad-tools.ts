/**
 * Scratchpad Drawing Tools for Gemini AI Teacher
 * 
 * These tools allow Gemini to draw on the whiteboard like a real teacher,
 * creating visual explanations, number lines, diagrams, and more.
 */
import { FunctionDeclaration, Type } from '@google/genai';

/**
 * Gemini function declarations for scratchpad drawing
 */
export const scratchpadTools: FunctionDeclaration[] = [
  {
    name: 'draw_line',
    description: 'Draw a straight line on the whiteboard. Use for underlining, crossing out, or connecting points.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        startX: { type: Type.NUMBER, description: 'Starting X coordinate (0-800)' },
        startY: { type: Type.NUMBER, description: 'Starting Y coordinate (0-600)' },
        endX: { type: Type.NUMBER, description: 'Ending X coordinate (0-800)' },
        endY: { type: Type.NUMBER, description: 'Ending Y coordinate (0-600)' },
        color: { type: Type.STRING, description: 'Line color (default: black). Options: black, red, blue, green, orange, purple' },
        width: { type: Type.NUMBER, description: 'Line thickness 1-8 (default: 2)' },
      },
      required: ['startX', 'startY', 'endX', 'endY'],
    },
  },
  {
    name: 'draw_arrow',
    description: 'Draw an arrow pointing from start to end. Use to point at things or show direction/movement.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        startX: { type: Type.NUMBER, description: 'Starting X coordinate (0-800)' },
        startY: { type: Type.NUMBER, description: 'Starting Y coordinate (0-600)' },
        endX: { type: Type.NUMBER, description: 'Arrow tip X coordinate (0-800)' },
        endY: { type: Type.NUMBER, description: 'Arrow tip Y coordinate (0-600)' },
        color: { type: Type.STRING, description: 'Arrow color (default: black)' },
        width: { type: Type.NUMBER, description: 'Arrow thickness 1-8 (default: 2)' },
      },
      required: ['startX', 'startY', 'endX', 'endY'],
    },
  },
  {
    name: 'draw_rectangle',
    description: 'Draw a rectangle. Use for boxing/highlighting important items, creating frames, or showing areas.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Top-left X coordinate (0-800)' },
        y: { type: Type.NUMBER, description: 'Top-left Y coordinate (0-600)' },
        width: { type: Type.NUMBER, description: 'Rectangle width in pixels' },
        height: { type: Type.NUMBER, description: 'Rectangle height in pixels' },
        color: { type: Type.STRING, description: 'Border color (default: black)' },
        fill: { type: Type.STRING, description: 'Fill color (default: transparent). Use light colors like #e3f2fd for subtle fill.' },
      },
      required: ['x', 'y', 'width', 'height'],
    },
  },
  {
    name: 'draw_circle',
    description: 'Draw a circle. Use for highlighting, grouping items, counting objects, or showing sets.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Center X coordinate (0-800)' },
        y: { type: Type.NUMBER, description: 'Center Y coordinate (0-600)' },
        radius: { type: Type.NUMBER, description: 'Circle radius in pixels' },
        color: { type: Type.STRING, description: 'Border color (default: black)' },
        fill: { type: Type.STRING, description: 'Fill color (default: transparent)' },
      },
      required: ['x', 'y', 'radius'],
    },
  },
  {
    name: 'draw_text',
    description: 'Write text on the whiteboard. Use for labels, equations, step numbers, or explanations.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Text X position (0-800)' },
        y: { type: Type.NUMBER, description: 'Text Y position (0-600)' },
        text: { type: Type.STRING, description: 'The text to write' },
        fontSize: { type: Type.NUMBER, description: 'Font size 12-48 (default: 20)' },
        color: { type: Type.STRING, description: 'Text color (default: black)' },
      },
      required: ['x', 'y', 'text'],
    },
  },
  {
    name: 'draw_number_line',
    description: 'Draw a number line with tick marks and labels. PERFECT for teaching addition, subtraction, and number concepts.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        startX: { type: Type.NUMBER, description: 'Left edge X position (default: 50)' },
        y: { type: Type.NUMBER, description: 'Y position for the line (default: 300)' },
        start: { type: Type.NUMBER, description: 'Starting number on the line' },
        end: { type: Type.NUMBER, description: 'Ending number on the line' },
        step: { type: Type.NUMBER, description: 'Increment between numbers (default: 1)' },
      },
      required: ['start', 'end'],
    },
  },
  {
    name: 'draw_fraction',
    description: 'Draw a fraction with numerator over denominator. Use when teaching fractions.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Center X position (0-800)' },
        y: { type: Type.NUMBER, description: 'Center Y position (0-600) - where the fraction line goes' },
        numerator: { type: Type.NUMBER, description: 'The top number' },
        denominator: { type: Type.NUMBER, description: 'The bottom number' },
        fontSize: { type: Type.NUMBER, description: 'Font size (default: 24)' },
      },
      required: ['x', 'y', 'numerator', 'denominator'],
    },
  },
  {
    name: 'draw_grid',
    description: 'Draw a grid of squares. Use for multiplication tables, area models, or organizing items.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Top-left X position (0-800)' },
        y: { type: Type.NUMBER, description: 'Top-left Y position (0-600)' },
        rows: { type: Type.NUMBER, description: 'Number of rows' },
        cols: { type: Type.NUMBER, description: 'Number of columns' },
        cellSize: { type: Type.NUMBER, description: 'Size of each cell in pixels (default: 40)' },
        color: { type: Type.STRING, description: 'Grid line color (default: black)' },
      },
      required: ['x', 'y', 'rows', 'cols'],
    },
  },
  {
    name: 'highlight_area',
    description: 'Highlight an area with a yellow semi-transparent overlay. Use to draw attention to something.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Top-left X position (0-800)' },
        y: { type: Type.NUMBER, description: 'Top-left Y position (0-600)' },
        width: { type: Type.NUMBER, description: 'Highlight width' },
        height: { type: Type.NUMBER, description: 'Highlight height' },
      },
      required: ['x', 'y', 'width', 'height'],
    },
  },
  {
    name: 'clear_whiteboard',
    description: 'Clear everything from the whiteboard. Use when starting a new topic or when the board is cluttered.',
    parameters: {
      type: Type.OBJECT,
      properties: {},
      required: [],
    },
  },
];

// Color mapping for convenience
const colorMap: Record<string, string> = {
  black: '#1e1e1e',
  red: '#e03131',
  blue: '#1971c2',
  green: '#2f9e44',
  orange: '#f76707',
  purple: '#7048e8',
  yellow: '#fab005',
  pink: '#e64980',
};

const getColor = (color?: string): string => {
  if (!color) return '#1e1e1e';
  return colorMap[color.toLowerCase()] || color;
};

/**
 * Execute a scratchpad tool call
 */
export const executeScratchpadTool = (
  toolCall: { name: string; args: Record<string, any> },
  scratchpad: {
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
): { success: boolean; message?: string } => {
  const { name, args } = toolCall;

  try {
    switch (name) {
      case 'draw_line':
        scratchpad.drawLine(
          args.startX,
          args.startY,
          args.endX,
          args.endY,
          getColor(args.color),
          args.width || 2
        );
        return { success: true, message: 'Line drawn' };

      case 'draw_arrow':
        scratchpad.drawArrow(
          args.startX,
          args.startY,
          args.endX,
          args.endY,
          getColor(args.color),
          args.width || 2
        );
        return { success: true, message: 'Arrow drawn' };

      case 'draw_rectangle':
        scratchpad.drawRectangle(
          args.x,
          args.y,
          args.width,
          args.height,
          getColor(args.color),
          args.fill || 'transparent'
        );
        return { success: true, message: 'Rectangle drawn' };

      case 'draw_circle':
        scratchpad.drawCircle(
          args.x,
          args.y,
          args.radius,
          getColor(args.color),
          args.fill || 'transparent'
        );
        return { success: true, message: 'Circle drawn' };

      case 'draw_text':
        scratchpad.drawText(
          args.x,
          args.y,
          args.text,
          args.fontSize || 20,
          getColor(args.color)
        );
        return { success: true, message: `Text "${args.text}" written` };

      case 'draw_number_line':
        scratchpad.drawNumberLine(
          args.startX || 50,
          args.y || 300,
          args.start,
          args.end,
          args.step || 1
        );
        return { success: true, message: `Number line from ${args.start} to ${args.end} drawn` };

      case 'draw_fraction':
        scratchpad.drawFraction(
          args.x,
          args.y,
          args.numerator,
          args.denominator,
          args.fontSize || 24
        );
        return { success: true, message: `Fraction ${args.numerator}/${args.denominator} drawn` };

      case 'draw_grid':
        scratchpad.drawGrid(
          args.x,
          args.y,
          args.rows,
          args.cols,
          args.cellSize || 40,
          getColor(args.color)
        );
        return { success: true, message: `${args.rows}x${args.cols} grid drawn` };

      case 'highlight_area':
        scratchpad.highlightArea(
          args.x,
          args.y,
          args.width,
          args.height
        );
        return { success: true, message: 'Area highlighted' };

      case 'clear_whiteboard':
        scratchpad.clearCanvas();
        return { success: true, message: 'Whiteboard cleared' };

      default:
        return { success: false, message: `Unknown tool: ${name}` };
    }
  } catch (error) {
    console.error(`Error executing ${name}:`, error);
    return { success: false, message: `Error: ${error}` };
  }
};
