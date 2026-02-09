/**
 * TutorDrawingHandler - Allows the AI tutor to draw on the teaching canvas
 *
 * This component registers a `draw_on_scratchpad` tool with the Gemini Live API
 * so the AI can add visual elements to the HTML5 Canvas whiteboard.
 *
 * KEY DESIGN DECISION — Simultaneous Talk + Draw:
 *   When Gemini calls draw_on_scratchpad, we send the tool response
 *   IMMEDIATELY (before animation starts), then queue the shapes for
 *   progressive rendering. This lets Gemini resume speaking instantly
 *   while the canvas animates asynchronously — replicating the
 *   "Sal Khan on a whiteboard" experience.
 */
import { useEffect, useRef, useCallback, memo } from "react";
import { useTutorContext } from "../../features/tutor";
import {
  FunctionDeclaration,
  LiveServerToolCall,
  Modality,
  Type,
} from "@google/genai";
import type { TeachingCanvasHandle } from "../teaching-canvas";
import type { ShapeDef } from "../teaching-canvas";

// ──────────────────────────────────────────────────────────
// Tool declaration — shape-based API
// ──────────────────────────────────────────────────────────
const drawDeclaration: FunctionDeclaration = {
  name: "draw_on_scratchpad",
  description: `Draw on the student's scratchpad to visually explain concepts.
Use the "shapes" parameter with a JSON array of shape objects.
The canvas is 800×600 pixels. Use coordinates within that range.

Available shapes:
- line: {"type":"line", "x1":num, "y1":num, "x2":num, "y2":num, "color":"#hex", "width":num}
- rect: {"type":"rect", "x":num, "y":num, "w":num, "h":num, "color":"#hex", "width":num}
- circle: {"type":"circle", "cx":num, "cy":num, "r":num, "color":"#hex", "width":num}
- arrow: {"type":"arrow", "x1":num, "y1":num, "x2":num, "y2":num, "color":"#hex", "width":num}
- text_label: {"type":"text_label", "x":num, "y":num, "text":"string", "color":"#hex", "size":num}
- number_line: {"type":"number_line", "x":num, "y":num, "length":num, "min":num, "max":num, "marks":[nums], "color":"#hex", "width":num}

Drawings animate progressively on screen so continue talking while they render.`,
  parameters: {
    type: Type.OBJECT,
    properties: {
      shapes: {
        type: Type.STRING,
        description: `JSON array of shape objects. Examples:
[{"type":"line","x1":100,"y1":300,"x2":700,"y2":300,"color":"#333","width":3}]
[{"type":"circle","cx":400,"cy":300,"r":80,"color":"#e03131","width":3}]
[{"type":"text_label","x":50,"y":50,"text":"Step 1","color":"#1971c2","size":20}]
[{"type":"number_line","x":50,"y":300,"length":700,"min":0,"max":10,"marks":[3,7],"color":"#333","width":2}]
[{"type":"arrow","x1":200,"y1":100,"x2":200,"y2":250,"color":"#e03131","width":3}]
[{"type":"rect","x":100,"y":100,"w":200,"h":150,"color":"#2f9e44","width":2}]`,
      },
      strokesJson: {
        type: Type.STRING,
        description: `Fallback: JSON array of raw freehand strokes. Each stroke: {"points":[{"x":num,"y":num}], "strokeColor":"#hex", "strokeWidth":num}`,
      },
      clearFirst: {
        type: Type.BOOLEAN,
        description: "If true, clear the canvas before drawing new content",
      },
    },
    required: [],
  },
};

// ──────────────────────────────────────────────────────────
// Parse raw strokesJson into ShapeDef[]
// ──────────────────────────────────────────────────────────
function rawStrokesToShapes(strokes: any[]): ShapeDef[] {
  return strokes
    .filter((s) => s && Array.isArray(s.points) && s.points.length > 0)
    .map((stroke) => ({
      type: "freehand" as const,
      points: stroke.points.map((p: { x: number; y: number }) => ({
        x: p.x,
        y: p.y,
      })),
      color: stroke.strokeColor || "#1e1e1e",
      width: stroke.strokeWidth || 4,
    }));
}

// ──────────────────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────────────────

function TutorDrawingHandlerComponent() {
  const { client, setConfig, config } = useTutorContext();
  const registeredRef = useRef(false);

  // Register the drawing tool with Gemini — only once
  useEffect(() => {
    if (registeredRef.current) return;

    const existingTools = config.tools || [];

    const hasDrawTool = existingTools.some((tool: any) =>
      tool.functionDeclarations?.some(
        (fd: any) => fd.name === "draw_on_scratchpad"
      )
    );

    if (!hasDrawTool) {
      registeredRef.current = true;
      const newTools = [
        ...existingTools,
        { functionDeclarations: [drawDeclaration] },
      ];

      setConfig({
        ...config,
        responseModalities: config.responseModalities || [Modality.AUDIO],
        tools: newTools,
      });

      console.log(
        "✅ TutorDrawingHandler: Registered draw_on_scratchpad tool (canvas-based)"
      );
    }
  }, [config, setConfig]);

  // Handle tool calls from Gemini
  useEffect(() => {
    const onToolCall = (toolCall: LiveServerToolCall) => {
      if (!toolCall.functionCalls) return;

      const drawCall = toolCall.functionCalls.find(
        (fc) => fc.name === "draw_on_scratchpad"
      );
      if (!drawCall) return;

      const args = drawCall.args as any;
      const canvasHandle = window.__teachingCanvasRef;

      if (!canvasHandle) {
        console.warn(
          "⚠️ TutorDrawingHandler: Teaching canvas not available."
        );
        // Send response immediately so Gemini doesn't hang
        client.sendToolResponse({
          functionResponses: [
            {
              response: {
                output: {
                  success: false,
                  error:
                    "The whiteboard is not available. Ask the student to open it first.",
                },
              },
              id: drawCall.id,
              name: drawCall.name,
            },
          ],
        });
        return;
      }

      // Parse shapes
      let shapes: ShapeDef[] = [];
      let textLabels: string[] = [];

      // 1) Process shapes (preferred)
      if (args.shapes) {
        try {
          const parsed = JSON.parse(args.shapes);
          if (Array.isArray(parsed)) {
            shapes.push(...parsed);
            // Extract text labels for the response
            for (const s of parsed) {
              if (s.type === "text_label" && s.text) {
                textLabels.push(s.text);
              }
            }
          }
        } catch (parseError) {
          console.error(
            "TutorDrawingHandler: Failed to parse shapes:",
            parseError
          );
        }
      }

      // 2) Process raw strokes (fallback)
      if (args.strokesJson) {
        try {
          const rawStrokes = JSON.parse(args.strokesJson);
          if (Array.isArray(rawStrokes)) {
            shapes.push(...rawStrokesToShapes(rawStrokes));
          }
        } catch (parseError) {
          console.error(
            "TutorDrawingHandler: Failed to parse strokesJson:",
            parseError
          );
        }
      }

      // ═══════════════════════════════════════════════════════
      // CRITICAL: Send tool response IMMEDIATELY — BEFORE animation starts.
      // This lets Gemini resume speaking while the canvas animates.
      // ═══════════════════════════════════════════════════════
      client.sendToolResponse({
        functionResponses: [
          {
            response: {
              output: {
                success: true,
                shapesQueued: shapes.length,
                ...(textLabels.length > 0 && { textLabels }),
              },
            },
            id: drawCall.id,
            name: drawCall.name,
          },
        ],
      });

      // Now queue the drawing for progressive animation (async, non-blocking)
      if (shapes.length > 0) {
        const clearFirst = args.clearFirst === true;
        canvasHandle.drawShapes(shapes, {
          animated: true,
          clearFirst,
          durationMs: Math.max(shapes.length * 500, 1500),
        });
      }

      console.log(
        `✅ TutorDrawingHandler: Queued ${shapes.length} shapes for animation` +
          (textLabels.length > 0
            ? ` (text: ${textLabels.join(", ")})`
            : "")
      );
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
