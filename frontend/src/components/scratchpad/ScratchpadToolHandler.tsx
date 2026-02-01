/**
 * ScratchpadToolHandler - Handles AI drawing tool calls
 * 
 * Listens to the TutorClient for drawing tool calls and executes them
 * on the scratchpad using the ScratchpadContext.
 */
import { useEffect } from 'react';
import { useTutorContext } from '../../features/tutor';
import { useScratchpad } from '../../contexts/ScratchpadContext';
import { executeScratchpadTool } from '../../features/tutor/scratchpad-tools';

const ScratchpadToolHandler: React.FC = () => {
  const { client } = useTutorContext();
  const scratchpad = useScratchpad();

  useEffect(() => {
    if (!client) return;

    const handleToolCall = (toolCall: any) => {
      console.log('🔧 Received tool call:', toolCall);

      // Check if this is a scratchpad tool
      const scratchpadToolNames = [
        'draw_line', 'draw_arrow', 'draw_rectangle', 'draw_circle',
        'draw_text', 'draw_number_line', 'draw_fraction', 'draw_grid',
        'highlight_area', 'clear_whiteboard'
      ];

      // Handle multiple function calls (Gemini can batch them)
      const functionCalls = toolCall.functionCalls || [];
      
      functionCalls.forEach((fc: any) => {
        if (scratchpadToolNames.includes(fc.name)) {
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

          // Send tool response back to Gemini
          if (client.sendToolResponse) {
            client.sendToolResponse({
              functionResponses: [{
                id: fc.id,
                name: fc.name,
                response: result,
              }],
            });
          }
        }
      });
    };

    // Subscribe to tool calls
    client.on('toolcall', handleToolCall);

    return () => {
      client.off('toolcall', handleToolCall);
    };
  }, [client, scratchpad]);

  // This component doesn't render anything
  return null;
};

export default ScratchpadToolHandler;
