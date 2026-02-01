/**
 * Scratchpad Tools - Gemini function declarations for AI teacher drawing
 * 
 * These tools allow Gemini to draw on the scratchpad like a real teacher,
 * creating visual explanations for math problems, diagrams, and concepts.
 */

import { FunctionDeclaration, Type } from '@google/genai';

/**
 * Tool declarations for Gemini to use the scratchpad
 */
export const scratchpadTools: FunctionDeclaration[] = [
  {
    name: 'draw_line',
    description: 'Draw a straight line on the whiteboard. Use this to underline, strike through, or connect points.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        startX: { type: Type.NUMBER, description: 'Starting X coordinate (0-800)' },
        startY: { type: Type.NUMBER, description: 'Starting Y coordinate (0-600)' },
        endX: { type: Type.NUMBER, description: 'Ending X coordinate (0-800)' },
        endY: { type: Type.NUMBER, description: 'Ending Y coordinate (0-600)' },
        color: { type: Type.STRING, description: 'Line color (e.g., "#1e1e1e", "#ff0000", "#4caf50")' },
      },
      required: ['startX', 'startY', 'endX', 'endY'],
    },
  },
  {
    name: 'draw_arrow',
    description: 'Draw an arrow on the whiteboard. Use this to point at things, show direction, or indicate flow.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        startX: { type: Type.NUMBER, description: 'Starting X coordinate' },
        startY: { type: Type.NUMBER, description: 'Starting Y coordinate' },
        endX: { type: Type.NUMBER, description: 'Ending X coordinate (arrow head)' },
        endY: { type: Type.NUMBER, description: 'Ending Y coordinate (arrow head)' },
        color: { type: Type.STRING, description: 'Arrow color' },
      },
      required: ['startX', 'startY', 'endX', 'endY'],
    },
  },
  {
    name: 'draw_rectangle',
    description: 'Draw a rectangle on the whiteboard. Use this to box/highlight areas, create frames, or show groups.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Top-left X coordinate' },
        y: { type: Type.NUMBER, description: 'Top-left Y coordinate' },
        width: { type: Type.NUMBER, description: 'Rectangle width' },
        height: { type: Type.NUMBER, description: 'Rectangle height' },
        color: { type: Type.STRING, description: 'Border color' },
        fill: { type: Type.STRING, description: 'Fill color (use "transparent" for no fill)' },
      },
      required: ['x', 'y', 'width', 'height'],
    },
  },
  {
    name: 'draw_circle',
    description: 'Draw a circle on the whiteboard. Use this for counting objects, Venn diagrams, or highlighting.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Center X coordinate' },
        y: { type: Type.NUMBER, description: 'Center Y coordinate' },
        radius: { type: Type.NUMBER, description: 'Circle radius' },
        color: { type: Type.STRING, description: 'Border color' },
        fill: { type: Type.STRING, description: 'Fill color (use "transparent" for no fill)' },
      },
      required: ['x', 'y', 'radius'],
    },
  },
  {
    name: 'draw_text',
    description: 'Write text on the whiteboard. Use this to label things, show steps, or write equations.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'X coordinate' },
        y: { type: Type.NUMBER, description: 'Y coordinate' },
        text: { type: Type.STRING, description: 'The text to write' },
        fontSize: { type: Type.NUMBER, description: 'Font size (default 20)' },
        color: { type: Type.STRING, description: 'Text color' },
      },
      required: ['x', 'y', 'text'],
    },
  },
  {
    name: 'draw_number_line',
    description: 'Draw a number line on the whiteboard. Perfect for teaching addition, subtraction, and number concepts.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Starting X coordinate' },
        y: { type: Type.NUMBER, description: 'Y coordinate' },
        start: { type: Type.NUMBER, description: 'Starting number on the line' },
        end: { type: Type.NUMBER, description: 'Ending number on the line' },
        highlight: { type: Type.NUMBER, description: 'Number to highlight/circle (optional)' },
      },
      required: ['x', 'y', 'start', 'end'],
    },
  },
  {
    name: 'draw_fraction',
    description: 'Draw a fraction on the whiteboard with a horizontal bar between numerator and denominator.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'X coordinate' },
        y: { type: Type.NUMBER, description: 'Y coordinate (for the fraction bar)' },
        numerator: { type: Type.NUMBER, description: 'Top number (numerator)' },
        denominator: { type: Type.NUMBER, description: 'Bottom number (denominator)' },
      },
      required: ['x', 'y', 'numerator', 'denominator'],
    },
  },
  {
    name: 'draw_grid',
    description: 'Draw a grid on the whiteboard. Perfect for multiplication, area models, or coordinate planes.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Top-left X coordinate' },
        y: { type: Type.NUMBER, description: 'Top-left Y coordinate' },
        rows: { type: Type.NUMBER, description: 'Number of rows' },
        cols: { type: Type.NUMBER, description: 'Number of columns' },
        cellSize: { type: Type.NUMBER, description: 'Size of each cell (default 40)' },
      },
      required: ['x', 'y', 'rows', 'cols'],
    },
  },
  {
    name: 'highlight_area',
    description: 'Highlight an area on the whiteboard with a semi-transparent yellow rectangle.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        x: { type: Type.NUMBER, description: 'Top-left X coordinate' },
        y: { type: Type.NUMBER, description: 'Top-left Y coordinate' },
        width: { type: Type.NUMBER, description: 'Width of highlight' },
        height: { type: Type.NUMBER, description: 'Height of highlight' },
      },
      required: ['x', 'y', 'width', 'height'],
    },
  },
  {
    name: 'clear_whiteboard',
    description: 'Clear the entire whiteboard to start fresh.',
    parameters: {
      type: Type.OBJECT,
      properties: {},
      required: [],
    },
  },
];

/**
 * Get the tool config for Gemini Live API
 */
export const getScratchpadToolConfig = () => ({
  functionDeclarations: scratchpadTools,
});

/**
 * Type for scratchpad tool call arguments
 */
export interface ScratchpadToolCall {
  name: string;
  args: Record<string, any>;
}

/**
 * Execute a scratchpad tool call
 */
export const executeScratchpadTool = (
  toolCall: ScratchpadToolCall,
  scratchpadFunctions: {
    drawLine: (startX: number, startY: number, endX: number, endY: number, color?: string, width?: number) => void;
    drawArrow: (startX: number, startY: number, endX: number, endY: number, color?: string) => void;
    drawRectangle: (x: number, y: number, width: number, height: number, color?: string, fill?: string) => void;
    drawCircle: (x: number, y: number, radius: number, color?: string, fill?: string) => void;
    drawText: (x: number, y: number, text: string, fontSize?: number, color?: string) => void;
    drawNumberLine: (x: number, y: number, start: number, end: number, highlight?: number) => void;
    drawFraction: (x: number, y: number, numerator: number, denominator: number) => void;
    drawGrid: (x: number, y: number, rows: number, cols: number, cellSize?: number) => void;
    highlightArea: (x: number, y: number, width: number, height: number) => void;
    clearCanvas: () => void;
  }
): { success: boolean; message: string } => {
  console.log('🎨 Executing scratchpad tool:', toolCall.name, toolCall.args);

  try {
    const { name, args } = toolCall;

    switch (name) {
      case 'draw_line':
        scratchpadFunctions.drawLine(
          args.startX, args.startY, args.endX, args.endY, args.color
        );
        return { success: true, message: 'Line drawn successfully' };

      case 'draw_arrow':
        scratchpadFunctions.drawArrow(
          args.startX, args.startY, args.endX, args.endY, args.color
        );
        return { success: true, message: 'Arrow drawn successfully' };

      case 'draw_rectangle':
        scratchpadFunctions.drawRectangle(
          args.x, args.y, args.width, args.height, args.color, args.fill
        );
        return { success: true, message: 'Rectangle drawn successfully' };

      case 'draw_circle':
        scratchpadFunctions.drawCircle(
          args.x, args.y, args.radius, args.color, args.fill
        );
        return { success: true, message: 'Circle drawn successfully' };

      case 'draw_text':
        scratchpadFunctions.drawText(
          args.x, args.y, args.text, args.fontSize, args.color
        );
        return { success: true, message: 'Text written successfully' };

      case 'draw_number_line':
        scratchpadFunctions.drawNumberLine(
          args.x, args.y, args.start, args.end, args.highlight
        );
        return { success: true, message: 'Number line drawn successfully' };

      case 'draw_fraction':
        scratchpadFunctions.drawFraction(
          args.x, args.y, args.numerator, args.denominator
        );
        return { success: true, message: 'Fraction drawn successfully' };

      case 'draw_grid':
        scratchpadFunctions.drawGrid(
          args.x, args.y, args.rows, args.cols, args.cellSize
        );
        return { success: true, message: 'Grid drawn successfully' };

      case 'highlight_area':
        scratchpadFunctions.highlightArea(
          args.x, args.y, args.width, args.height
        );
        return { success: true, message: 'Area highlighted successfully' };

      case 'clear_whiteboard':
        scratchpadFunctions.clearCanvas();
        return { success: true, message: 'Whiteboard cleared successfully' };

      default:
        return { success: false, message: `Unknown tool: ${name}` };
    }
  } catch (error) {
    console.error('Error executing scratchpad tool:', error);
    return { success: false, message: `Error: ${error}` };
  }
};
