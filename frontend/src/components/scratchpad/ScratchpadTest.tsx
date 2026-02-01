import React from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

/**
 * Standalone test page for tldraw scratchpad
 */
const ScratchpadTest = () => {
  return (
    <div style={{ width: "100vw", height: "100vh", position: "fixed", inset: 0 }}>
      <Tldraw />
    </div>
  );
};

export default ScratchpadTest;
