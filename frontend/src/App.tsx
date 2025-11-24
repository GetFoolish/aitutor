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
import SidePanel from "./components/side-panel/SidePanel";
import MediaMixerDisplay from "./components/media-mixer-display/MediaMixerDisplay";
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import ControlTray from "./components/control-tray/ControlTray";
import Scratchpad from "./components/scratchpad/Scratchpad";

function App() {
  // this video reference is used for displaying the active stream, whether that is the webcam or screen capture
  // feel free to style as you see fit
  const videoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  // either the screen capture, the video or null, if null we hide it
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);
  const mixerVideoRef = useRef<HTMLVideoElement>(null);
  const [commandSocket, setCommandSocket] = useState<WebSocket | null>(null);
  const [videoSocket, setVideoSocket] = useState<WebSocket | null>(null);
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);

  useEffect(() => {
    // Command WebSocket for sending frames/commands TO MediaMixer
    const commandWsUrl = import.meta.env.VITE_MEDIAMIXER_COMMAND_WS || 'ws://localhost:8765/command';
    const commandWs = new WebSocket(commandWsUrl);
    setCommandSocket(commandWs);

    // Video WebSocket for receiving video FROM MediaMixer
    const videoWsUrl = import.meta.env.VITE_MEDIAMIXER_VIDEO_WS || 'ws://localhost:8765/video';
    const videoWs = new WebSocket(videoWsUrl);
    setVideoSocket(videoWs);

    return () => {
      commandWs.close();
      videoWs.close();
    };
  }, []);

  useEffect(() => {
    if (mixerVideoRef.current && mixerStream) {
      mixerVideoRef.current.srcObject = mixerStream;
    }
  }, [mixerStream]);

  return (
    <div className="App">
      <LiveAPIProvider>
        <div className="streaming-console">
          <SidePanel />
          <main>
            <div className="main-app-area">
              <div className="question-panel" style={{border: '2px solid red'}}>
                <ScratchpadCapture socket={commandSocket}>
                  <QuestionDisplay />
                  {isScratchpadOpen && (
                    <div className="scratchpad-container">
                      <Scratchpad />
                    </div>
                  )}
                </ScratchpadCapture>
              </div>
              <MediaMixerDisplay socket={videoSocket} renderCanvasRef={renderCanvasRef} />
            </div>

            <ControlTray
              socket={commandSocket}
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
      </LiveAPIProvider>
    </div>
  );
}

export default App;
