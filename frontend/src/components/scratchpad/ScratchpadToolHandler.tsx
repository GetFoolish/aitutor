/**
 * ScratchpadToolHandler - Handles AI Teacher drawing tool calls
 * 
 * Listens to the TutorClient for drawing tool calls from Gemini
 * and executes them on the scratchpad using the ScratchpadContext.
 */
import { useEffect } from 'react';
import { useTutorContext } from '../../features/tutor';
import { useScratchpad } from '../../contexts/ScratchpadContext';
import { executeScratchpadTool } from '../../features/tutor/scratchpad-tools';

// List of tool names that are scratchpad drawing tools
const SCRATCHPAD_TOOL_NAMES = [
  'draw_line',
  'draw_arrow', 
  'draw_rectangle',
  'draw_circle',
  'draw_text',
  'draw_number_line',
  'draw_fraction',
  'draw_grid',
  'highlight_area',
  'clear_whiteboard',
];

const ScratchpadToolHandler: React.FC = () => {
  const { client } = useTutorContext();
  const scratchpad = useScratchpad();

  useEffect(() => {
    if (!client) return;

    const handleToolCall = (toolCall: any) => {
      console.log('🔧 Received tool call:', toolCall);

      // Handle multiple function calls (Gemini can batch them)
      const functionCalls = toolCall.functionCalls || [];
      const scratchpadResponses: any[] = [];

      functionCalls.forEach((fc: any) => {
        // Check if this is a scratchpad tool
        if (SCRATCHPAD_TOOL_NAMES.includes(fc.name)) {
          console.log('🎨 AI Teacher drawing:', fc.name, fc.args);

          // Execute the drawing command
          const result = executeScratchpadTool(
            { name: fc.name, args: fc.args || {} },
            {
              drawLine: scratchpad.drawLine,
              drawArrow: scratchpad.drawArrow,
              drawRectangle: scratchpad.drawRectangle,
              drawCircle: scratchpad.drawCircle,
              drawText: scratchpad.drawText,
              drawNumberLine: scratchpad.drawNumberLine,
              drawFraction: scratchpad.drawFraction,
              drawGrid: scratchpad.drawGrid,
              highlightArea: scratchpad.highlightArea,
              clearCanvas: scratchpad.clearCanvas,
            }
          );

          scratchpadResponses.push({
            id: fc.id,
            name: fc.name,
            response: { output: result },
          });
        }
      });

      // Send tool responses back to Gemini for scratchpad tools we handled
      if (scratchpadResponses.length > 0 && client.sendToolResponse) {
        setTimeout(() => {
          client.sendToolResponse({
            functionResponses: scratchpadResponses,
          });
        }, 100); // Small delay to ensure drawing is rendered
      }
    };

    // Subscribe to tool calls
    client.on('toolcall', handleToolCall);

    return () => {
      client.off('toolcall', handleToolCall);
    };
  }, [client, scratchpad]);

  // This component doesn't render anything visible
  return null;
};

export default ScratchpadToolHandler;
