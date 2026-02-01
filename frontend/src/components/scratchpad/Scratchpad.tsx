import React from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

/**
 * Scratchpad component using tldraw for drawing/whiteboard functionality.
 * 
 * Features:
 * - Full drawing tools (pencil, shapes, text, arrows)
 * - Undo/redo support
 * - Pan and zoom
 * - Export capabilities
 * 
 * Replaced Excalidraw due to stability issues.
 */
const Scratchpad: React.FC = () => {
  return (
    <div style={{ width: "100%", height: "100%", minHeight: "400px" }}>
      <Tldraw />
    </div>
  );
};

export default Scratchpad;
