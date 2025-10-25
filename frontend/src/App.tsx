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
import { BrowserRouter, Switch, Route } from "react-router-dom";
import "./App.scss";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import MediaMixerDisplay from "./components/media-mixer-display/MediaMixerDisplay";
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import ControlTray from "./components/control-tray/ControlTray";
import { LiveClientOptions } from "./types";
import Scratchpad from "./components/scratchpad/Scratchpad";
import RendererComponent from "./components/question-widget-renderer/RendererComponent"
import QuestionValidationComponent from "./components/question-widget-renderer/QuestionValidationComponent";

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY as string;
if (typeof API_KEY !== "string") {
  throw new Error("set VITE_GEMINI_API_KEY in .env");
}

const apiOptions: LiveClientOptions = {
  apiKey: API_KEY,
};

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
    const commandWs = new WebSocket('ws://localhost:8765');
    setCommandSocket(commandWs);

    // Video WebSocket for receiving video FROM MediaMixer
    const videoWs = new WebSocket('ws://localhost:8766');
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
    <BrowserRouter>
      <Switch>
        <Route exact path="/">
          <div className="App">
            <LiveAPIProvider options={apiOptions}>
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
        </Route>
        <Route path="/:id">
          <RendererComponent />
        </Route>
        <Route path="/admin/question-validation">
          <QuestionValidationComponent />
        </Route>
      </Switch>
    </BrowserRouter>
  );
}

export default App;
