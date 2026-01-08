/**
 * TutorDrawingHandler - Allows the AI tutor to draw on the scratchpad
 *
 * This component registers a tool with the Gemini Live API that enables
 * the AI tutor to add visual elements to the react-sketch-canvas scratchpad.
 */
import { useEffect, useRef, memo } from "react";
import { useTutorContext } from "../../features/tutor";
import {
  FunctionDeclaration,
  LiveServerToolCall,
  Modality,
  Type,
} from "@google/genai";

// Function declaration for the draw_on_scratchpad tool
// Simplified schema for Gemini compatibility
const drawDeclaration: FunctionDeclaration = {
  name: "draw_on_scratchpad",
  description: "Draw on the student's scratchpad. Use for visual explanations, diagrams, number lines, graphs. Provide strokes as JSON string with points array.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      strokesJson: {
        type: Type.STRING,
        description: "JSON string of strokes array. Each stroke: {points: [{x, y}], strokeColor: '#hex', strokeWidth: number}. Example: [{\"points\":[{\"x\":100,\"y\":100},{\"x\":200,\"y\":200}],\"strokeColor\":\"#ff0000\",\"strokeWidth\":4}]",
      },
      clearFirst: {
        type: Type.BOOLEAN,
        description: "If true, clear the scratchpad before drawing",
      },
    },
    required: ["strokesJson"],
  },
};

// Convert stroke data to react-sketch-canvas CanvasPath format
function convertToCanvasPaths(strokes: any[]): any[] {
  return strokes.map((stroke, index) => ({
    drawMode: true,
    strokeColor: stroke.strokeColor || "#1e1e1e",
    strokeWidth: stroke.strokeWidth || 4,
    paths: stroke.points.map((point: { x: number; y: number }) => ({
      x: point.x,
      y: point.y,
    })),
  }));
}

function TutorDrawingHandlerComponent() {
  const { client, setConfig, config } = useTutorContext();
  const isDrawingRef = useRef(false);

  // Register the drawing tool with Gemini
  useEffect(() => {
    // Get existing tools from config
    const existingTools = config.tools || [];

    // Check if our tool is already registered
    const hasDrawTool = existingTools.some((tool: any) => {
      if (tool.functionDeclarations) {
        return tool.functionDeclarations.some((fd: any) => fd.name === "draw_on_scratchpad");
      }
      return false;
    });

    if (!hasDrawTool) {
      // Add our drawing tool to existing tools
      const newTools = [
        ...existingTools,
        { functionDeclarations: [drawDeclaration] },
      ];

      setConfig({
        ...config,
        responseModalities: config.responseModalities || [Modality.AUDIO],
        tools: newTools,
      });

      console.log("✅ TutorDrawingHandler: Registered draw_on_scratchpad tool");
    }
  }, [config, setConfig]);

  // Handle tool calls from Gemini
  useEffect(() => {
    const onToolCall = (toolCall: LiveServerToolCall) => {
      if (!toolCall.functionCalls) {
        return;
      }

      const drawCall = toolCall.functionCalls.find(
        (fc) => fc.name === "draw_on_scratchpad"
      );

      if (drawCall && !isDrawingRef.current) {
        isDrawingRef.current = true;

        try {
          const args = drawCall.args as any;
          const sketchCanvas = window.__sketchCanvasRef;

          if (!sketchCanvas) {
            console.warn("⚠️ TutorDrawingHandler: Sketch canvas not available. Is the scratchpad open?");
            client.sendToolResponse({
              functionResponses: [{
                response: { output: { success: false, error: "Scratchpad is not open. Ask the student to open the scratchpad first." } },
                id: drawCall.id,
                name: drawCall.name,
              }],
            });
            isDrawingRef.current = false;
            return;
          }

          // Clear if requested
          if (args.clearFirst) {
            sketchCanvas.clearCanvas();
          }

          // Parse strokes from JSON string
          let strokes: any[] = [];
          try {
            strokes = JSON.parse(args.strokesJson || "[]");
          } catch (parseError) {
            console.error("Failed to parse strokesJson:", parseError);
            strokes = [];
          }

          // Convert strokes to canvas paths
          const canvasPaths = convertToCanvasPaths(strokes);

          // Load the paths onto the canvas
          if (canvasPaths.length > 0) {
            sketchCanvas.loadPaths(canvasPaths);
          }

          console.log(`✅ TutorDrawingHandler: Added ${canvasPaths.length} strokes to scratchpad`);

          // Send success response
          setTimeout(() => {
            client.sendToolResponse({
              functionResponses: [{
                response: { output: { success: true, strokesAdded: canvasPaths.length } },
                id: drawCall.id,
                name: drawCall.name,
              }],
            });
            isDrawingRef.current = false;
          }, 100);

        } catch (error) {
          console.error("❌ TutorDrawingHandler: Error drawing on scratchpad:", error);
          client.sendToolResponse({
            functionResponses: [{
              response: { output: { success: false, error: String(error) } },
              id: drawCall.id,
              name: drawCall.name,
            }],
          });
          isDrawingRef.current = false;
        }
      }
    };

    client.on("toolcall", onToolCall);

    return () => {
      client.off("toolcall", onToolCall);
    };
  }, [client]);

  // This component doesn't render anything visible
  return null;
}

export const TutorDrawingHandler = memo(TutorDrawingHandlerComponent);
export default TutorDrawingHandler;
