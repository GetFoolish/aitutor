/**
 * Hook for receiving and executing AI drawing commands on tldraw
 *
 * Listens for data channel messages from the LiveKit agent and
 * executes drawing commands on the tldraw canvas.
 */

import { useEffect, useCallback, useRef } from 'react';
import { Editor, createShapeId, TLShapeId } from 'tldraw';
import { Room, DataPacket_Kind } from 'livekit-client';

interface DrawingCommand {
  action: string;
  [key: string]: any;
}

interface ScratchpadMessage {
  type: 'scratchpad_command';
  command: DrawingCommand;
}

// Track AI-created shape IDs for cleanup
const AI_SHAPE_PREFIX = 'ai-drawing-';

export function useAIDrawing(editor: Editor | null, room: Room | null) {
  const aiShapeIds = useRef<Set<TLShapeId>>(new Set());

  // Convert percentage coordinates (0-100) to canvas coordinates
  const toCanvasCoords = useCallback((x: number, y: number): { x: number; y: number } => {
    if (!editor) return { x: 0, y: 0 };

    // Get viewport bounds
    const viewport = editor.getViewportScreenBounds();
    const canvasX = (x / 100) * viewport.width;
    const canvasY = (y / 100) * viewport.height;

    // Convert screen to page coordinates
    const pagePoint = editor.screenToPage({ x: canvasX, y: canvasY });
    return pagePoint;
  }, [editor]);

  // Generate unique AI shape ID
  const createAIShapeId = useCallback((): TLShapeId => {
    const id = createShapeId(`${AI_SHAPE_PREFIX}${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
    aiShapeIds.current.add(id);
    return id;
  }, []);

  // Clear all AI drawings
  const clearAIDrawings = useCallback(() => {
    if (!editor) return;

    const idsToDelete = Array.from(aiShapeIds.current);
    if (idsToDelete.length > 0) {
      editor.deleteShapes(idsToDelete);
      aiShapeIds.current.clear();
    }
    console.log('[AIDrawing] Cleared AI drawings');
  }, [editor]);

  // Execute a drawing command
  const executeCommand = useCallback((command: DrawingCommand) => {
    if (!editor) {
      console.warn('[AIDrawing] No editor available');
      return;
    }

    console.log('[AIDrawing] Executing command:', command.action);

    try {
      switch (command.action) {
        case 'draw_line': {
          const start = toCanvasCoords(command.start_x, command.start_y);
          const end = toCanvasCoords(command.end_x, command.end_y);

          editor.createShape({
            id: createAIShapeId(),
            type: 'line',
            x: start.x,
            y: start.y,
            props: {
              start: { x: 0, y: 0 },
              end: { x: end.x - start.x, y: end.y - start.y },
              color: command.color?.replace('#', '') || 'black',
              size: command.stroke_width > 3 ? 'l' : command.stroke_width > 1.5 ? 'm' : 's',
            },
          });
          break;
        }

        case 'draw_arrow': {
          const start = toCanvasCoords(command.start_x, command.start_y);
          const end = toCanvasCoords(command.end_x, command.end_y);

          editor.createShape({
            id: createAIShapeId(),
            type: 'arrow',
            x: start.x,
            y: start.y,
            props: {
              start: { x: 0, y: 0 },
              end: { x: end.x - start.x, y: end.y - start.y },
              color: command.color === '#e63946' ? 'red' : 'black',
              size: command.stroke_width > 3 ? 'l' : 'm',
              arrowheadEnd: 'arrow',
            },
          });
          break;
        }

        case 'draw_circle': {
          const center = toCanvasCoords(command.center_x, command.center_y);
          const radiusInPixels = (command.radius / 100) * editor.getViewportScreenBounds().width;

          editor.createShape({
            id: createAIShapeId(),
            type: 'geo',
            x: center.x - radiusInPixels,
            y: center.y - radiusInPixels,
            props: {
              geo: 'ellipse',
              w: radiusInPixels * 2,
              h: radiusInPixels * 2,
              color: command.color?.replace('#', '') || 'black',
              fill: command.fill ? 'solid' : 'none',
            },
          });
          break;
        }

        case 'draw_rectangle': {
          const pos = toCanvasCoords(command.x, command.y);
          const viewport = editor.getViewportScreenBounds();
          const width = (command.width / 100) * viewport.width;
          const height = (command.height / 100) * viewport.height;

          editor.createShape({
            id: createAIShapeId(),
            type: 'geo',
            x: pos.x,
            y: pos.y,
            props: {
              geo: 'rectangle',
              w: width,
              h: height,
              color: command.color?.replace('#', '') || 'black',
              fill: command.fill ? 'solid' : 'none',
            },
          });
          break;
        }

        case 'write_text': {
          const pos = toCanvasCoords(command.x, command.y);

          editor.createShape({
            id: createAIShapeId(),
            type: 'text',
            x: pos.x,
            y: pos.y,
            props: {
              text: command.text,
              color: command.color?.replace('#', '') || 'black',
              size: command.font_size > 20 ? 'l' : command.font_size > 14 ? 'm' : 's',
              font: 'draw',
            },
          });
          break;
        }

        case 'highlight_area': {
          const pos = toCanvasCoords(command.x, command.y);
          const viewport = editor.getViewportScreenBounds();
          const width = (command.width / 100) * viewport.width;
          const height = (command.height / 100) * viewport.height;

          editor.createShape({
            id: createAIShapeId(),
            type: 'geo',
            x: pos.x,
            y: pos.y,
            props: {
              geo: 'rectangle',
              w: width,
              h: height,
              color: 'yellow',
              fill: 'semi',
              opacity: 0.3,
            },
          });
          break;
        }

        case 'clear_ai_drawings': {
          clearAIDrawings();
          break;
        }

        default:
          console.warn('[AIDrawing] Unknown command:', command.action);
      }
    } catch (error) {
      console.error('[AIDrawing] Error executing command:', error);
    }
  }, [editor, toCanvasCoords, createAIShapeId, clearAIDrawings]);

  // Listen for data channel messages from LiveKit
  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: DataPacket_Kind,
      topic?: string
    ) => {
      // Only process scratchpad messages
      if (topic !== 'scratchpad') return;

      try {
        const text = new TextDecoder().decode(payload);
        const message: ScratchpadMessage = JSON.parse(text);

        if (message.type === 'scratchpad_command' && message.command) {
          executeCommand(message.command);
        }
      } catch (error) {
        console.error('[AIDrawing] Error parsing data message:', error);
      }
    };

    room.on('dataReceived', handleDataReceived);
    console.log('[AIDrawing] Listening for AI drawing commands');

    return () => {
      room.off('dataReceived', handleDataReceived);
    };
  }, [room, executeCommand]);

  return {
    clearAIDrawings,
    executeCommand,
  };
}
