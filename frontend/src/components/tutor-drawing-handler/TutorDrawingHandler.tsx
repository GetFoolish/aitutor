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
import { useOptionalTutorContext } from "../../features/tutor/TutorContext";
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
  description: `Draw on the student's whiteboard (canvas) to visually explain concepts.
The whiteboard is your PRIMARY teaching tool. Whenever a student asks a question or shows a problem, you MUST automatically start teaching it visually on the canvas while speaking.

Use the "shapes" parameter with an array of shape objects.
The canvas is 800×600 pixels. Use coordinates within that range.

Available shapes:
- line: {"type":"line", "x1":num, "y1":num, "x2":num, "y2":num, "color":"#hex", "width":num}
- rect: {"type":"rect", "x":num, "y":num, "w":num, "h":num, "color":"#hex", "width":num}
- filled_rect: {"type":"filled_rect", "x":num, "y":num, "w":num, "h":num, "color":"#hex", "fill":"#hex", "width":num}
- circle: {"type":"circle", "cx":num, "cy":num, "r":num, "color":"#hex", "width":num}
- filled_circle: {"type":"filled_circle", "cx":num, "cy":num, "r":num, "color":"#hex", "fill":"#hex", "width":num}
- arrow: {"type":"arrow", "x1":num, "y1":num, "x2":num, "y2":num, "color":"#hex", "width":num}
- text_label: {"type":"text_label", "x":num, "y":num, "text":"string", "color":"#hex", "size":num}
- number_line: {"type":"number_line", "x":num, "y":num, "length":num, "min":num, "max":num, "marks":[nums], "color":"#hex", "width":num}

IMPORTANT: Build explanations step by step across multiple calls. Clear the whiteboard with clearFirst:true before starting a new problem. ALWAYS narrate what you are drawing as it appears.`,
  parameters: {
    type: Type.OBJECT,
    properties: {
      shapes: {
        type: Type.ARRAY,
        description: "Array of shape objects to render on the whiteboard",
        items: {
          type: Type.OBJECT,
          properties: {
            type: {
              type: Type.STRING,
              description: "Shape type: line, rect, circle, arrow, text_label, etc.",
            },
            x: { type: Type.NUMBER },
            y: { type: Type.NUMBER },
            x1: { type: Type.NUMBER },
            y1: { type: Type.NUMBER },
            x2: { type: Type.NUMBER },
            y2: { type: Type.NUMBER },
            w: { type: Type.NUMBER },
            h: { type: Type.NUMBER },
            cx: { type: Type.NUMBER },
            cy: { type: Type.NUMBER },
            r: { type: Type.NUMBER },
            text: { type: Type.STRING },
            size: { type: Type.NUMBER },
            color: { type: Type.STRING, description: "Hex color code" },
            fill: { type: Type.STRING, description: "Hex fill color code" },
            width: { type: Type.NUMBER, description: "Stroke width" },
            length: { type: Type.NUMBER },
            min: { type: Type.NUMBER },
            max: { type: Type.NUMBER },
            marks: {
              type: Type.ARRAY,
              items: { type: Type.NUMBER },
            },
          },
        },
      },
      clearFirst: {
        type: Type.BOOLEAN,
        description: "If true, clear the whiteboard before drawing new content",
      },
      strokesJson: {
        type: Type.STRING,
        description: "Fallback: JSON array of raw freehand strokes",
      },
    },
    required: ["shapes"],
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
  const tutorContext = useOptionalTutorContext();
  const registeredRef = useRef(false);

  const client = tutorContext?.client;
  const setConfig = tutorContext?.setConfig;
  const config = tutorContext?.config;

  // Register the drawing tool with Gemini — only once
  useEffect(() => {
    if (!config || !setConfig) return;
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

      // Always ensure AUDIO is in responseModalities - don't overwrite if already set correctly
      const currentModalities = config.responseModalities || [];
      const hasAudio = currentModalities.includes(Modality.AUDIO);
      const finalModalities = hasAudio ? currentModalities : [...currentModalities, Modality.AUDIO];
      
      setConfig({
        ...config,
        responseModalities: finalModalities.length > 0 ? finalModalities : [Modality.AUDIO],
        tools: newTools,
      });
      
      console.log(`[TutorDrawingHandler] Config updated - responseModalities:`, finalModalities);

      console.log(
        "✅ TutorDrawingHandler: Registered draw_on_scratchpad tool (canvas-based)"
      );
    }
  }, [config, setConfig]);

  // Handle tool calls from Gemini
  useEffect(() => {
    if (!client) return;

    const onToolCall = (toolCall: LiveServerToolCall) => {
      if (!toolCall.functionCalls) return;

      const drawCall = toolCall.functionCalls.find(
        (fc) => fc.name === "draw_on_scratchpad"
      );
      if (!drawCall) return;

      const args = drawCall.args as any;
      console.log("🎨 TutorDrawingHandler: Received draw_on_scratchpad call:", args);
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
        let parsedShapes: any[] = [];
        if (typeof args.shapes === "string") {
          try {
            parsedShapes = JSON.parse(args.shapes);
          } catch (parseError) {
            console.error(
              "TutorDrawingHandler: Failed to parse shapes string:",
              parseError
            );
          }
        } else if (Array.isArray(args.shapes)) {
          // Check if array elements are JSON strings and parse them
          parsedShapes = args.shapes.map(item => {
            if (typeof item === "string") {
              try {
                return JSON.parse(item);
              } catch (parseError) {
                console.warn("TutorDrawingHandler: Failed to parse shape string:", item);
                return item;
              }
            }
            return item;
          });
        }

        if (parsedShapes.length > 0) {
          console.log(`🎨 TutorDrawingHandler: Normalizing ${parsedShapes.length} shapes`);
          console.log(`🎨 TutorDrawingHandler: Raw shapes before normalization:`, JSON.stringify(parsedShapes.slice(0, 2), null, 2));

          // Normalize coordinates (ensure numbers)
          const normalized = parsedShapes.map(s => {
            // Skip if s is not an object (shouldn't happen after parsing, but safety check)
            if (typeof s !== "object" || s === null || Array.isArray(s)) {
              console.warn("TutorDrawingHandler: Invalid shape object:", s);
              return null;
            }
            const n = { ...s };
            ['x', 'y', 'w', 'h', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'width', 'size'].forEach(prop => {
              if (s[prop] !== undefined) n[prop] = Number(s[prop]);
            });
            return n;
          }).filter(s => s !== null); // Remove any null entries

          console.log(`🎨 TutorDrawingHandler: Normalized shapes:`, JSON.stringify(normalized.slice(0, 2), null, 2));
          shapes.push(...normalized);
          // Extract text labels for the response
          for (const s of normalized) {
            if (s.type === "text_label" && s.text) {
              textLabels.push(s.text);
            }
          }
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
      const clearFirst = args.clearFirst === true;
      if (shapes.length > 0 || clearFirst) {
        console.log(`🎨 TutorDrawingHandler: Executing drawShapes`, {
          clearFirst,
          shapesCount: shapes.length,
          firstShape: shapes[0],
          canvasHandle: !!canvasHandle
        });
        canvasHandle.drawShapes(shapes, {
          animated: true,
          clearFirst,
          durationMs: Math.max(shapes.length * 500, 1500),
        });
      } else {
        console.warn(`🎨 TutorDrawingHandler: No shapes to draw and clearFirst=false`);
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
