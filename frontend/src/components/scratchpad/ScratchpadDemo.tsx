import React, { useState } from "react";
import Scratchpad from "./Scratchpad";
import { Button } from "@/components/ui/button";

/**
 * Demo page showing the scratchpad as it would appear in the tutoring interface
 */
const ScratchpadDemo = () => {
  const [isScratchpadOpen, setScratchpadOpen] = useState(true);

  return (
    <div className="min-h-screen bg-[#FFFDF5] relative">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b-4 border-black bg-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 border-4 border-black bg-[#FFD93D] flex items-center justify-center shadow-[4px_4px_0_0_#000]">
            <span className="material-symbols-outlined text-xl">smart_toy</span>
          </div>
          <span className="font-black text-xl">teachr<span className="text-xs bg-red-500 text-white px-1 rounded ml-1">LIVE</span></span>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={() => setScratchpadOpen(!isScratchpadOpen)}
            className={`h-10 px-4 border-4 border-black shadow-[4px_4px_0_0_#000] font-bold ${
              isScratchpadOpen ? 'bg-[#FFD93D]' : 'bg-white'
            }`}
          >
            <span className="material-symbols-outlined mr-2">brush</span>
            {isScratchpadOpen ? 'Hide Scratchpad' : 'Show Scratchpad'}
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Question Area */}
        <div className="flex-1 p-6">
          <div className="max-w-2xl mx-auto">
            <div className="border-4 border-black bg-white p-6 shadow-[8px_8px_0_0_#000]">
              <div className="bg-[#FFD93D] -mx-6 -mt-6 mb-6 px-6 py-3 border-b-4 border-black">
                <span className="font-black uppercase text-sm">Math Question</span>
              </div>
              <p className="text-lg mb-6">
                hey! 🦖 so your friend leo has 7 boxes for his dinosaur collection. 
                he wants to put 6 dino figures in each box. 
                how many dinosaurs will leo have in total?
              </p>
              <div className="flex items-center gap-4">
                <input 
                  type="text" 
                  placeholder="your answer..."
                  className="flex-1 px-4 py-3 border-4 border-black focus:outline-none focus:ring-2 focus:ring-[#FFD93D]"
                />
                <Button className="h-12 px-6 bg-[#7C3AED] text-white border-4 border-black shadow-[4px_4px_0_0_#000] font-bold">
                  SUBMIT
                </Button>
              </div>
            </div>
            
            <p className="text-center mt-6 text-gray-500">
              ← Use the scratchpad on the right to work out your answer! →
            </p>
          </div>
        </div>

        {/* Scratchpad Panel */}
        {isScratchpadOpen && (
          <div className="w-[500px] border-l-4 border-black bg-white">
            <div className="h-full flex flex-col">
              <div className="bg-[#FFD93D] px-4 py-2 border-b-4 border-black flex items-center justify-between">
                <span className="font-black uppercase text-sm">✏️ Scratchpad</span>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setScratchpadOpen(false)}
                  className="h-6 w-6 p-0"
                >
                  ✕
                </Button>
              </div>
              <div className="flex-1">
                <Scratchpad />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScratchpadDemo;
