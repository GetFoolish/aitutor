import React, { useState, useRef, useEffect } from 'react';
import { Camera, Mic, Video, Home, Bell, MoreHorizontal, Wand2, FileText, Palette, X, Settings, Eye, Pause, Square } from 'lucide-react';

export default function LoomRecordingWidget({children}) {
  const [position, setPosition] = useState({ x: 50, y: 50 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isRecording, setIsRecording] = useState(false);
  const [isWidgetVisible, setIsWidgetVisible] = useState(true);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedOption, setSelectedOption] = useState('Full screen');
  const [cameraStream, setCameraStream] = useState(null);
  const [screenStream, setScreenStream] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const [micStream, setMicStream] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0); // For visual feedback
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const widgetRef = useRef(null);
  const videoRef = useRef(null);
  const timerRef = useRef(null);
  const dragStartPos = useRef(null);

  // --- Floating button dragging state ---
  const [floatingButtonPosition, setFloatingButtonPosition] = useState({ x: 50, y: 150 });
  const [isFloatingButtonDragging, setIsFloatingButtonDragging] = useState(false);
  const [floatingButtonDragOffset, setFloatingButtonDragOffset] = useState({ x: 0, y: 0 });

  // --- Camera avatar dragging state ---
  const [cameraPosition, setCameraPosition] = useState({ x: 0, y: 0 });
  const [isCameraDragging, setIsCameraDragging] = useState(false);
  const [cameraDragOffset, setCameraDragOffset] = useState({ x: 0, y: 0 });
  const cameraRef = useRef(null);

  // Initialize camera avatar position at bottom-right on mount
  useEffect(() => {
    const setInitialCameraPos = () => {
      const avatarSize = 160; // width/height of avatar container
      const margin = 24;
      setCameraPosition({
        x: window.innerWidth - avatarSize - margin,
        y: window.innerHeight - avatarSize - margin
      });
    };

    // Only run in browser
    if (typeof window !== 'undefined') {
      setInitialCameraPos();
      // adjust if window resizes so avatar doesn't disappear
      const handleResize = () => setInitialCameraPos();
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  // Attach mouse/touch handlers for the widget dragging (existing)
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  // Attach mouse/touch handlers for camera avatar dragging
  useEffect(() => {
    const handleCameraMove = (e) => {
      if (!isCameraDragging) return;
      // support both mouse and touch
      const clientX = e.clientX ?? (e.touches && e.touches[0].clientX);
      const clientY = e.clientY ?? (e.touches && e.touches[0].clientY);
      if (clientX == null || clientY == null) return;

      setCameraPosition({
        x: clientX - cameraDragOffset.x,
        y: clientY - cameraDragOffset.y
      });
    };

    const handleCameraUp = () => {
      setIsCameraDragging(false);
    };

    if (isCameraDragging) {
      document.addEventListener('mousemove', handleCameraMove);
      document.addEventListener('mouseup', handleCameraUp);
      document.addEventListener('touchmove', handleCameraMove, { passive: false });
      document.addEventListener('touchend', handleCameraUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleCameraMove);
      document.removeEventListener('mouseup', handleCameraUp);
      document.removeEventListener('touchmove', handleCameraMove);
      document.removeEventListener('touchend', handleCameraUp);
    };
  }, [isCameraDragging, cameraDragOffset]);

  // Attach mouse handlers for the floating button dragging
  useEffect(() => {
    const handleFloatingButtonMove = (e) => {
      if (isFloatingButtonDragging) {
        setFloatingButtonPosition({
          x: e.clientX - floatingButtonDragOffset.x,
          y: e.clientY - floatingButtonDragOffset.y
        });
      }
    };

    const handleFloatingButtonUp = () => {
      setIsFloatingButtonDragging(false);
    };

    if (isFloatingButtonDragging) {
      document.addEventListener('mousemove', handleFloatingButtonMove);
      document.addEventListener('mouseup', handleFloatingButtonUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleFloatingButtonMove);
      document.removeEventListener('mouseup', handleFloatingButtonUp);
    };
  }, [isFloatingButtonDragging, floatingButtonDragOffset]);

  useEffect(() => {
    if (cameraStream && videoRef.current) {
      videoRef.current.srcObject = cameraStream;
    }
  }, [cameraStream]);

  useEffect(() => {
    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
      }
      if (screenStream) {
        screenStream.getTracks().forEach(track => track.stop());
      }
      if (micStream) { // Add micStream cleanup
        micStream.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) { // Add audioContext cleanup
        audioContextRef.current.close();
      }
    };
  }, [cameraStream, screenStream, micStream]);

  const handleMouseDown = (e) => {
    if (widgetRef.current && !e.target.closest('button')) {
      const rect = widgetRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
      setIsDragging(true);
    }
  };

  // Camera avatar mouse/touch start
  const handleCameraMouseDown = (e) => {
    // Prevent the parent widget from starting a drag
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setCameraDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
    setIsCameraDragging(true);
  };

  const handleCameraTouchStart = (e) => {
    e.stopPropagation();
    e.preventDefault();
    const touch = e.touches[0];
    const rect = e.currentTarget.getBoundingClientRect();
    setCameraDragOffset({
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top
    });
    setIsCameraDragging(true);
  };

  const handleStartRecording = async () => {
    try {
      // Request screen recording permission
      const screen = await navigator.mediaDevices.getDisplayMedia({
        video: { mediaSource: 'screen' },
        audio: true
      });

      setScreenStream(screen);

      // If camera is enabled, request camera permission
      let camera = null;
      if (cameraEnabled) {
        try {
          camera = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
          });
          setCameraStream(camera);
        } catch (err) {
          console.error('Camera permission denied:', err);
          alert('Camera permission was denied. Recording will continue without camera.');
        }
      }

      // Combine streams
      const tracks = [...screen.getTracks()];
      if (camera) {
        tracks.push(...camera.getVideoTracks());
      }
      if (micStream) { // Add mic audio tracks if mic is enabled
        tracks.push(...micStream.getAudioTracks());
      }

      const combinedStream = new MediaStream(tracks);

      // Create media recorder
      const recorder = new MediaRecorder(combinedStream, {
        mimeType: 'video/webm;codecs=vp8,opus'
      });

      const chunks = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        // The blob can be used for other purposes (e.g., preview, upload)
        // but automatic download is removed as per request.
        // const url = URL.createObjectURL(blob);
        // const a = document.createElement('a');
        // a.href = url;
        // a.download = `loom-recording-${Date.now()}.webm`;
        // a.click();
        // URL.revokeObjectURL(url);
      };
  

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setRecordingTime(0);
      setIsPaused(false); // Ensure recording starts unpaused

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 300) { // 5 minutes limit
            handleStopRecording();
            return 300;
          }
          return prev + 1;
        });
      }, 1000);

      // Handle screen share stop
      screen.getVideoTracks()[0].onended = () => {
        handleStopRecording();
      };

    } catch (err) {
      console.error('Error starting recording:', err);
      alert('Failed to start recording. Please ensure you grant the necessary permissions.');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }

    if (screenStream) {
      screenStream.getTracks().forEach(track => track.stop());
      setScreenStream(null);
    }

    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }

    if (micStream) {
      micStream.getTracks().forEach(track => track.stop());
      setMicStream(null);
      setMicEnabled(false);
      setAudioLevel(0);
    }

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsRecording(false);
    setRecordingTime(0);
    setMediaRecorder(null);
    setIsPaused(false); // Reset paused state on stop
  };

  const handlePauseRecording = () => {
    if (mediaRecorder) {
      if (!isPaused) {
        mediaRecorder.pause();
        if (timerRef.current) {
          clearInterval(timerRef.current);
        }
      } else {
        mediaRecorder.resume();
        timerRef.current = setInterval(() => {
          setRecordingTime(prev => {
            if (prev >= 300) { // 5 minutes limit
              handleStopRecording();
              return 300;
            }
            return prev + 1;
          });
        }, 1000);
      }
      setIsPaused(!isPaused);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleOptionSelect = (option) => {
    setSelectedOption(option);
    setShowDropdown(false);
  };

  const handleFloatingButtonMouseDown = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setFloatingButtonDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
    setIsFloatingButtonDragging(true);
  };

  const toggleMicrophone = async () => {
    if (micEnabled) {
      // Turn off microphone
      if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        setMicStream(null);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      setMicEnabled(false);
      setAudioLevel(0);
    } else {
      // Turn on microphone
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setMicStream(stream);
        setMicEnabled(true);

        // Setup audio analysis for visual feedback
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        const microphone = audioContext.createMediaStreamSource(stream);

        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        microphone.connect(analyser);
        // analyser.connect(audioContext.destination); // Connect to destination if you want to hear yourself

        audioContextRef.current = audioContext;
        analyserRef.current = analyser;
        dataArrayRef.current = dataArray;

        const updateAudioLevel = () => {
          analyser.getByteFrequencyData(dataArray);
          const sum = dataArray.reduce((a, b) => a + b, 0);
          const average = sum / bufferLength;
          setAudioLevel(average);
          if (micEnabled) { // Only continue if mic is still enabled
            requestAnimationFrame(updateAudioLevel);
          }
        };
        requestAnimationFrame(updateAudioLevel);

      } catch (err) {
        console.error('Microphone permission denied:', err);
        alert('Microphone permission was denied.');
        setMicEnabled(false);
      }
    }
  };

  return (
    <div className="">
      {isWidgetVisible ? (
        <div
          ref={widgetRef}
          className="absolute bg-white rounded-2xl shadow-2xl w-80 cursor-move select-none z-20"
          style={{
            left: `${position.x}px`,
            top: `${position.y}px`,
          }}
          onMouseDown={handleMouseDown}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <button onClick={() => setIsWidgetVisible(false)} className="hover:bg-gray-100 p-2 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-4 space-y-3">
            {/* Full Screen Button with Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="w-full bg-purple-100 hover:bg-purple-200 text-purple-700 font-medium py-3 px-4 rounded-xl transition-colors flex items-center gap-3"
              >
                <Video className="w-5 h-5" />
                <span>{selectedOption}</span>
              </button>

              {showDropdown && (
                <div className="absolute  -right-64 -top-8  bg-white rounded-xl shadow-xl border border-gray-200 py-2 z-10">
                  <button
                    onClick={() => handleOptionSelect('Full screen')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3"
                  >
                    <Video className="w-5 h-5 text-purple-600" />
                    <div>
                      <div className="font-medium text-gray-800">Full screen</div>
                      <div className="text-xs text-blue-600">Select</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleOptionSelect('Specific window')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3"
                  >
                    <div className="w-5 h-5 border-2 border-gray-400 rounded"></div>
                    <span className="text-gray-800">Specific window</span>
                  </button>
                  <button
                    onClick={() => handleOptionSelect('Custom size')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3"
                  >
                    <div className="w-5 h-5 border-2 border-gray-300 rounded border-dashed"></div>
                    <div className="flex-1 flex items-center justify-between">
                      <span className="text-gray-400">Custom size</span>
                      <span className="text-xs text-blue-600">Upgrade</span>
                    </div>
                  </button>
                  <div className="border-t border-gray-200 mt-2 pt-2">
                    <div className="px-4 py-2 text-sm font-medium text-gray-500">More</div>
                    <button className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3">
                      <Camera className="w-5 h-5 text-gray-600" />
                      <span className="text-gray-800">Camera only</span>
                    </button>
                    <button className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3">
                      <div className="w-5 h-5 border-2 border-gray-600 rounded"></div>
                      <span className="text-gray-800">Screenshot</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* No Camera Button */}
            <button
              onClick={() => setCameraEnabled(!cameraEnabled)}
              className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-4 rounded-xl transition-colors flex items-center gap-3"
            >
              <Camera className={`w-5 h-5 ${cameraEnabled ? 'text-green-600' : 'text-red-500'}`} />
              <span>{cameraEnabled ? 'Camera' : 'No Camera'}</span>
            </button>

            {/* Microphone Status */}
            <button
              onClick={toggleMicrophone}
              className="w-full bg-gray-50 hover:bg-gray-100 rounded-xl py-3 px-4 flex items-center justify-between transition-colors"
            >
              <div className="flex items-center gap-3">
                <Mic className={`w-5 h-5 ${micEnabled ? 'text-green-600' : 'text-gray-600'}`} />
                <span className="text-sm font-medium text-gray-700">
                  {micEnabled ? 'Microphone On' : 'Microphone Off'}
                </span>
                {micEnabled && (
                  <div className="flex items-center gap-1">
                    {/* Simple audio bars */}
                    {[...Array(3)].map((_, i) => (
                      <div
                        key={i}
                        className="w-1 h-4 bg-green-500 rounded-full transition-all duration-75"
                        style={{ transform: `scaleY(${Math.min(1, audioLevel / 100) * (0.5 + i * 0.25)})` }}
                      ></div>
                    ))}
                  </div>
                )}
              </div>
              <span className={`text-xs font-bold px-3 py-1 rounded-full ${micEnabled ? 'bg-green-400 text-white' : 'bg-red-400 text-white'}`}>
                {micEnabled ? 'On' : 'Off'}
              </span>
            </button>

            {/* Start Recording Button */}
            <button
              onClick={isRecording ? handleStopRecording : handleStartRecording}
              className={`w-full font-bold py-4 rounded-xl transition-all shadow-lg ${
                isRecording
                  ? 'bg-red-500 hover:bg-red-600 text-white'
                  : 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white'
              }`}
            >
              {isRecording ? `Stop recording (${formatTime(recordingTime)})` : 'Start recording'}
            </button>

            {/* Recording Limit */}
            <p className="text-center text-sm text-gray-500">
              {isRecording ? `${formatTime(300 - recordingTime)} remaining` : '5 min recording limit'}
            </p>

            {/* Bottom Icons */}
            <div className="flex items-center justify-around pt-2 border-t border-gray-200">
              <button className="flex flex-col items-center gap-1 p-2 hover:bg-gray-50 rounded-lg transition-colors">
                <Settings className="w-5 h-5 text-gray-600" />
                <span className="text-xs text-gray-600">Settings</span>
              </button>
              <button className="flex flex-col items-center gap-1 p-2 hover:bg-gray-50 rounded-lg transition-colors">
                <Eye className="w-5 h-5 text-gray-600" />
                <span className="text-xs text-gray-600">View</span>
              </button>
              <button className="flex flex-col items-center gap-1 p-2 hover:bg-gray-50 rounded-lg transition-colors">
                <MoreHorizontal className="w-5 h-5 text-gray-600" />
                <span className="text-xs text-gray-600">More</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onMouseDown={handleFloatingButtonMouseDown}
          onClick={() => setIsWidgetVisible(true)}
          className="absolute bg-purple-600 text-white rounded-full w-16 h-16 flex items-center justify-center shadow-2xl cursor-move z-20"
          style={{
            left: `${floatingButtonPosition.x}px`,
            top: `${floatingButtonPosition.y}px`,
          }}
        >
          <Eye className="w-8 h-8" />
        </button>
      )}

      {/* Camera Avatar Preview (now draggable) */}
      {cameraStream && (
        <div
          ref={cameraRef}
          onMouseDown={handleCameraMouseDown}
          onTouchStart={handleCameraTouchStart}
          className="absolute rounded-full overflow-hidden shadow-2xl border-4 border-white cursor-grab"
          style={{
            zIndex: 1000,
            width: 160,
            height: 160,
            left: `${cameraPosition.x}px`,
            top: `${cameraPosition.y}px`
          }}
        >
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover pointer-events-none"
          />
        </div>
      )}



      {/* Recording Control Popup */}
      {isRecording && (
        <div className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-gray-800 text-white p-3 rounded-lg shadow-xl z-50 flex flex-col items-center space-y-3">
          <span className="text-lg font-bold">{formatTime(recordingTime)}</span>
          <button
            onClick={handlePauseRecording}
            className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 transition-colors cursor-pointer"
          >
            {isPaused ? <Video className="w-5 h-5" /> : <Pause className="w-5 h-5" />}
          </button>
          <button
            onClick={handleStopRecording}
            className="p-2 rounded-full bg-red-500 hover:bg-red-600 transition-colors cursor-pointer"
          >
            <Square className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Instructions */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full">
        {isRecording ? 'Recording in progress...' : 'Drag the widget anywhere on the screen'}
      </div>

      {children}
    </div>
  );
}
