import React from "react";
import Scratchpad from "./components/scratchpad/Scratchpad";

export default function App(): JSX.Element {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-[800px] h-[600px] border border-gray-300 p-2 bg-white">
        <Scratchpad />
      </div>
    </div>
  );
}
