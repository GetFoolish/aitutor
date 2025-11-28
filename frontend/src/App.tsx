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
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import ControlTray from "./components/control-tray/ControlTray";
import Scratchpad from "./components/scratchpad/Scratchpad";
import { useMediaMixer } from "./hooks/useMediaMixer";
import { useMediaCapture } from "./hooks/useMediaCapture";
import "./components/media-mixer-display/media-mixer-display.scss";

function App() {
  // this video reference is used for displaying the active stream, whether that is the webcam or screen capture
  // feel free to style as you see fit
  const videoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  // either the screen capture, the video or null, if null we hide it
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);
  const mixerVideoRef = useRef<HTMLVideoElement>(null);
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);

  // Ref to hold mediaMixer instance for use in callbacks
  const mediaMixerRef = useRef<any>(null);

  // Media capture with frame callbacks - must be called before useMediaMixer
  const { cameraEnabled, screenEnabled, toggleCamera, toggleScreen } = useMediaCapture({
    onCameraFrame: (imageData) => {
      mediaMixerRef.current?.updateCameraFrame(imageData);
    },
    onScreenFrame: (imageData) => {
      mediaMixerRef.current?.updateScreenFrame(imageData);
    }
  });

  // MediaMixer hook for local video mixing - uses state from useMediaCapture
  const mediaMixer = useMediaMixer({
    width: 1280,
    height: 2160,
    fps: 10,
    quality: 0.85,
    cameraEnabled: cameraEnabled,
    screenEnabled: screenEnabled
  });

  // Store mediaMixer in ref for use in callbacks
  useEffect(() => {
    mediaMixerRef.current = mediaMixer;
  }, [mediaMixer]);

  // Start mixer when component mounts and canvas is available
  useEffect(() => {
    if (mediaMixer.canvasRef.current) {
      mediaMixer.setIsRunning(true);
      return () => {
        mediaMixer.setIsRunning(false);
      };
    }
  }, [mediaMixer]);

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
                <ScratchpadCapture onFrameCaptured={(imageData) => {
                  mediaMixer.updateScratchpadFrame(imageData);
                }}>
                  <QuestionDisplay />
                  {isScratchpadOpen && (
                    <div className="scratchpad-container">
                      <Scratchpad />
                    </div>
                  )}
                </ScratchpadCapture>
              </div>

              {/* Direct canvas display - no WebSocket needed */}
              <div className="media-mixer-display">
                <div className="media-mixer-content">
                  <canvas
                    ref={(canvas) => {
                      // Set both refs to the same canvas element
                      mediaMixer.canvasRef.current = canvas;
                      renderCanvasRef.current = canvas;
                    }}
                    width={1280}
                    height={2160}
                    style={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: 'contain'
                    }}
                  />
                </div>
              </div>
            </div>

            <ControlTray
              renderCanvasRef={renderCanvasRef}
              videoRef={videoRef}
              supportsVideo={true}
              onVideoStreamChange={setVideoStream}
              onMixerStreamChange={setMixerStream}
              enableEditingSettings={true}
              cameraEnabled={cameraEnabled}
              screenEnabled={screenEnabled}
              onToggleCamera={toggleCamera}
              onToggleScreen={toggleScreen}
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
