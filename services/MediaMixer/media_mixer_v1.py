#!/usr/bin/env python3
"""
Python MediaMixer - Combines camera, screen share, and scratchpad streams
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mss
import time
import base64
import io
from typing import Optional, Callable
import os
import asyncio
import websockets
import signal
import sys

import json


class MediaMixer:
    """Combines camera, screen share, and scratchpad streams"""
    
    def __init__(self, 
                 output_width: int = 1280, 
                 output_height: int = 2160,
                 fps: int = 15,
                 on_mixed_frame: Optional[Callable[[str], None]] = None):
        
        self.output_width = output_width
        self.output_height = output_height
        self.fps = fps
        self.on_mixed_frame = on_mixed_frame
        self.scratchpad_frame: Optional[np.ndarray] = None
        
        # Section dimensions (each section is 1280x720)
        self.section_width = output_width
        self.section_height = output_height // 3
        
        # Initialize components
        self.camera = None
        try:
            self.screen_capture = mss.mss()
            print("Screen capture initialized successfully")
        except Exception as e:
            self.screen_capture = None
            print(f"Could not initialize screen capture: {e}")
        
        # Control flags
        self.running = False
        self.show_preview = False
        self.show_camera = False
        self.show_screen = False
        self._cleanup_called = False

        # Resources will be armed when toggle commands are received
        print("MediaMixer initialized - waiting for toggle commands")

    def _init_camera(self):
        """Initialize camera capture"""
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                print("Warning: Could not open camera")
                self.camera = None
            else:
                # Set camera resolution
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                print("Camera initialized successfully")
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.camera = None
    
    def get_camera_frame(self) -> Optional[np.ndarray]:
        """Capture frame from camera"""
        if not self.camera or not self.show_camera:
            return None
        
        ret, frame = self.camera.read()
        if not ret:
            return None
        
        # Resize to section dimensions
        frame = cv2.resize(frame, (self.section_width, self.section_height))
        return frame
    
    def get_screen_frame(self) -> Optional[np.ndarray]:
        """Capture screen frame"""
        if not self.show_screen:
            return None
        try:
            # Get the primary monitor
            monitor = self.screen_capture.monitors[1]  # 0 is all monitors, 1 is primary
            
            # Capture screen
            screenshot = self.screen_capture.grab(monitor)
            
            # Convert to numpy array
            frame = np.array(screenshot)
            
            # Convert BGRA to BGR (remove alpha channel)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Resize to section dimensions
            frame = cv2.resize(frame, (self.section_width, self.section_height))
            
            return frame
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def mix_frames(self, scratchpad_current: Optional[np.ndarray] = None) -> np.ndarray:
        """Mix all three video sources into a single frame"""
        # Create output canvas
        mixed_frame = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        
        # Get frames from all sources
        if scratchpad_current is None:
            # Create a blank white frame
            scratchpad_frame = np.ones((self.section_height, self.section_width, 3), dtype=np.uint8) * 255
        else:
            scratchpad_frame = cv2.resize(scratchpad_current, (self.section_width, self.section_height))

        screen_frame = self.get_screen_frame()
        camera_frame = self.get_camera_frame()
        
        # Section 1: Scratchpad (always present)
        y_offset = 0
        mixed_frame[y_offset:y_offset + self.section_height, :] = scratchpad_frame
        
        # Section 2: Screen share (if available)
        y_offset = self.section_height
        if screen_frame is not None:
            mixed_frame[y_offset:y_offset + self.section_height, :] = screen_frame
        else:
            # Fill with black if no screen share
            mixed_frame[y_offset:y_offset + self.section_height, :] = 0
        
        # Section 3: Camera (if available)
        y_offset = 2 * self.section_height
        if camera_frame is not None:
            mixed_frame[y_offset:y_offset + self.section_height, :] = camera_frame
        else:
            # Fill with dark gray if no camera
            mixed_frame[y_offset:y_offset + self.section_height, :] = 64
        
        return mixed_frame
    
    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Convert OpenCV frame to base64 JPEG string"""
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        
        # Convert to base64
        base64_data = base64.b64encode(buffer).decode('utf-8')
        
        return base64_data
    
    def stop(self):
        """Stop the mixer and cleanup resources"""
        if self._cleanup_called:
            return

        self._cleanup_called = True
        self.running = False

        print("Stopping MediaMixer...")

        # Release camera resources immediately
        if self.camera:
            print("Releasing camera resources...")
            self.camera.release()
            self.camera = None

        # Cleanup OpenCV windows
        cv2.destroyAllWindows()
        print("MediaMixer stopped")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop()

async def handler(websocket):
    print(f"Client connected: {websocket.remote_address}")
    mixer = MediaMixer()
    mixer.running = True

    async def send_frames():
        frame_interval = 1/mixer.fps  # 67ms for 15 FPS
        sleep_chunk = 0.01  # 10ms chunks for responsive shutdown

        while mixer.running:
            try:
                mixed_frame = mixer.mix_frames(scratchpad_current=mixer.scratchpad_frame)
                base64_frame = mixer.frame_to_base64(mixed_frame)
                await websocket.send(base64_frame)

                # Sleep in small chunks to be responsive to shutdown
                elapsed = 0
                while elapsed < frame_interval and mixer.running:
                    await asyncio.sleep(sleep_chunk)
                    elapsed += sleep_chunk

            except websockets.exceptions.ConnectionClosed:
                print("Client disconnected")
                mixer.running = False
                break
            except Exception as e:
                print(f"Error in send_frames: {e}")
                mixer.running = False
                break

    async def receive_commands():
        while mixer.running:
            try:
                message = await websocket.recv()
                # All messages must be valid JSON with our standardized format
                data = json.loads(message)
                if data.get('type') == 'scratchpad_frame':
                    base64_data = data['data'].split(',')[1]
                    img_bytes = base64.b64decode(base64_data)
                    img = Image.open(io.BytesIO(img_bytes))
                    # Convert RGB from browser to BGR for OpenCV
                    mixer.scratchpad_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                elif data.get('type') == 'toggle_camera':
                    mixer.show_camera = data.get('data', {}).get('enabled', False)
                    print(f"Camera toggled: {'ON' if mixer.show_camera else 'OFF'}")
                    # Release camera immediately if disabled
                    if not mixer.show_camera and mixer.camera:
                        print("Releasing camera resources (toggled off)...")
                        mixer.camera.release()
                        mixer.camera = None
                    elif mixer.show_camera and not mixer.camera:
                        print("Re-initializing camera (toggled on)...")
                        mixer._init_camera()
                elif data.get('type') == 'toggle_screen':
                    mixer.show_screen = data.get('data', {}).get('enabled', False)
                    print(f"Screen share toggled: {'ON' if mixer.show_screen else 'OFF'}")
                else:
                    print(f"Unknown command type: {data.get('type')}")

            except websockets.exceptions.ConnectionClosed:
                mixer.running = False
                break
            except Exception as e:
                print(f"Error processing message: {e}")

    send_task = asyncio.create_task(send_frames())
    receive_task = asyncio.create_task(receive_commands())

    try:
        await asyncio.gather(send_task, receive_task)
    except asyncio.CancelledError:
        print("Tasks cancelled during shutdown")
    finally:
        print(f"Client {websocket.remote_address} disconnected, cleaning up...")

        # Cancel tasks immediately
        send_task.cancel()
        receive_task.cancel()

        # Wait briefly for clean cancellation
        try:
            await asyncio.gather(send_task, receive_task, return_exceptions=True)
        except:
            pass

        mixer.stop()

async def main():
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        # Use asyncio's thread-safe method to set the event
        asyncio.get_event_loop().call_soon_threadsafe(shutdown_event.set)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server = None
    try:
        server = await websockets.serve(handler, "localhost", 8765)
        print("WebSocket server started on ws://localhost:8765")
        print("Press Ctrl+C to stop")

        # Wait for shutdown signal
        await shutdown_event.wait()
        print("Shutdown signal received, closing server...")

    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        if server:
            server.close()
            await server.wait_closed()
            print("Server closed")
        print("Server shutdown complete")

if __name__ == '__main__':
    asyncio.run(main())