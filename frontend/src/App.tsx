/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useRef, useState, useEffect } from "react";
import "./App.scss";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import { TABridgeProvider } from "./contexts/TABridgeContext";
import SidePanel from "./components/side-panel/SidePanel";
import { Altair } from "./components/altair/Altair";
import MediaMixerDisplay from "./components/media-mixer-display/MediaMixerDisplay";
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import ControlTray from "./components/control-tray/ControlTray";
import cn from "classnames";
import { LiveClientOptions } from "./types";
import Scratchpad from "./components/scratchpad/Scratchpad";

const API_KEY = process.env.REACT_APP_GEMINI_API_KEY as string;
if (typeof API_KEY !== "string") {
  throw new Error("set REACT_APP_GEMINI_API_KEY in .env");
}

const apiOptions: LiveClientOptions = {
  apiKey: API_KEY,
};

// Inner component that has access to LiveAPIContext
function AppInner() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);
  const mixerVideoRef = useRef<HTMLVideoElement>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);

  // Initialize MediaMixer WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8765');
    setSocket(ws);

    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    if (mixerVideoRef.current && mixerStream) {
      mixerVideoRef.current.srcObject = mixerStream;
    }
  }, [mixerStream]);

  return (
    <div className="streaming-console">
      <SidePanel />
      <main>
        <div className="main-app-area">
          <div className="question-panel">
            <ScratchpadCapture socket={socket}>
              <QuestionDisplay />
              {isScratchpadOpen && (
                <div className="scratchpad-container">
                  <Scratchpad />
                </div>
              )}
            </ScratchpadCapture>
          </div>
          <MediaMixerDisplay socket={socket} renderCanvasRef={renderCanvasRef} />
        </div>

        <ControlTray
          socket={socket}
          renderCanvasRef={renderCanvasRef}
          videoRef={videoRef}
          supportsVideo={true}
          onVideoStreamChange={setVideoStream}
          onMixerStreamChange={setMixerStream}
          enableEditingSettings={true}
        >
          <button onClick={() => setScratchpadOpen(!isScratchpadOpen)}>
            <span className="material-symbols-outlined">
              {isScratchpadOpen ? "close" : "edit"}
            </span>
          </button>
        </ControlTray>
      </main>
    </div>
  );
}

// Main App component wrapper
function App() {
  return (
    <div className="App">
      <LiveAPIProvider options={apiOptions}>
        <TABridgeProvider>
          <AppInner />
        </TABridgeProvider>
      </LiveAPIProvider>
    </div>
  );
}

export default App;
