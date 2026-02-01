import React, { useState } from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

/**
 * Demo page showing the scratchpad alongside a sample math question.
 * Access at: /test/demo
 */
const ScratchpadDemo: React.FC = () => {
  const [showScratchpad, setShowScratchpad] = useState(true);

  return (
    <div style={{ 
      display: "flex", 
      flexDirection: "column", 
      height: "100vh",
      background: "#FFFDF5"
    }}>
      {/* Header */}
      <header style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "12px 24px",
        borderBottom: "3px solid #000",
        background: "#FFFDF5"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "24px" }}>🤖</span>
          <span style={{ fontWeight: 900, fontSize: "20px" }}>teachr</span>
          <span style={{ 
            background: "#FF6B6B", 
            color: "white", 
            padding: "2px 8px", 
            borderRadius: "4px",
            fontSize: "12px",
            fontWeight: 700
          }}>LIVE</span>
        </div>
        <button
          onClick={() => setShowScratchpad(!showScratchpad)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            background: "#FFD93D",
            border: "3px solid #000",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: 700
          }}
        >
          <span>✏️</span>
          {showScratchpad ? "Hide Scratchpad" : "Show Scratchpad"}
        </button>
      </header>

      {/* Main content */}
      <div style={{ 
        display: "flex", 
        flex: 1, 
        overflow: "hidden",
        padding: "24px",
        gap: "24px"
      }}>
        {/* Question panel */}
        <div style={{ 
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <div style={{
            background: "#FFD93D",
            border: "3px solid #000",
            borderRadius: "12px",
            padding: "24px",
            maxWidth: "600px",
            width: "100%",
            boxShadow: "4px 4px 0 #000"
          }}>
            <div style={{ 
              fontWeight: 900, 
              textTransform: "uppercase",
              marginBottom: "16px"
            }}>
              Math Question
            </div>
            <p style={{ fontSize: "18px", lineHeight: 1.6 }}>
              hey! 🦖 so your friend leo has 7 boxes for his dinosaur collection. 
              he wants to put 6 dino figures in each box. how many dinosaurs will 
              leo have in total?
            </p>
            <div style={{ marginTop: "24px", display: "flex", gap: "12px" }}>
              <input
                type="text"
                placeholder="your answer..."
                style={{
                  flex: 1,
                  padding: "12px",
                  border: "3px solid #000",
                  borderRadius: "8px",
                  fontSize: "16px"
                }}
              />
              <button style={{
                padding: "12px 24px",
                background: "#6C63FF",
                color: "white",
                border: "3px solid #000",
                borderRadius: "8px",
                fontWeight: 700,
                cursor: "pointer"
              }}>
                SUBMIT
              </button>
            </div>
          </div>
          <p style={{ marginTop: "16px", color: "#666" }}>
            ← Use the scratchpad on the right to work out your answer! →
          </p>
        </div>

        {/* Scratchpad panel */}
        {showScratchpad && (
          <div style={{
            width: "450px",
            display: "flex",
            flexDirection: "column",
            border: "3px solid #000",
            borderRadius: "12px",
            overflow: "hidden",
            boxShadow: "4px 4px 0 #000"
          }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 16px",
              background: "#FFF5E6",
              borderBottom: "3px solid #000"
            }}>
              <span style={{ fontWeight: 700 }}>✏️ Scratchpad</span>
              <button
                onClick={() => setShowScratchpad(false)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "18px"
                }}
              >
                ✕
              </button>
            </div>
            <div style={{ flex: 1, position: "relative" }}>
              <Tldraw />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScratchpadDemo;
