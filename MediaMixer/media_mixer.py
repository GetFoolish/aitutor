#!/usr/bin/env python3
"""
Clean MediaMixer - Combines camera, screen share, and scratchpad streams
"""

import cv2
import numpy as np
from PIL import Image
import mss
import base64
import io
import asyncio
import websockets
import signal
import json


class MediaMixer:
    """Clean MediaMixer implementation"""

    def __init__(self, width=2560, height=4320, fps=15):  # High resolution for crisp text readability
        self.width = width
        self.height = height
        self.fps = fps
        self.section_height = height // 3

        # State
        self.running = False
        self.show_camera = False
        self.show_screen = True  # Enable screen sharing by default for Pipecat integration
        self.camera = None
        self.screen_capture = mss.mss()
        self.scratchpad_frame = None

        print("MediaMixer initialized - screen sharing ENABLED by default")

    def init_camera(self):
        """Initialize camera when needed"""
        if not self.camera:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                print("Camera initialized successfully")
            else:
                print("Warning: Could not open camera")
                self.camera = None

    def release_camera(self):
        """Release camera resources"""
        if self.camera:
            print("Releasing camera resources...")
            self.camera.release()
            self.camera = None

    def get_camera_frame(self):
        """Get camera frame if enabled"""
        if not self.show_camera or not self.camera:
            return None

        ret, frame = self.camera.read()
        if ret:
            return cv2.resize(frame, (self.width, self.section_height))
        return None

    def get_screen_frame(self):
        """Get screen frame if enabled"""
        if not self.show_screen:
            return None

        try:
            # Capture primary monitor (monitors[1])
            # monitors[0] = all monitors combined
            # monitors[1] = primary display
            monitor = self.screen_capture.monitors[1]
            screenshot = self.screen_capture.grab(monitor)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return cv2.resize(frame, (self.width, self.section_height))
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None

    def mix_frames(self):
        """Mix all sources into single frame with smart layout"""
        camera_frame = self.get_camera_frame()
        screen_frame = self.get_screen_frame()

        # If both screen AND scratchpad are available, use 2-section vertical layout
        if screen_frame is not None and self.scratchpad_frame is not None:
            # Create 2-section layout (1920x2160 = 1920x1080 * 2)
            dual_height = self.width  # Square sections for readability
            mixed_frame = np.zeros((dual_height * 2, self.width, 3), dtype=np.uint8)

            # Top half: Scratchpad
            scratchpad = cv2.resize(self.scratchpad_frame, (self.width, dual_height))
            mixed_frame[0:dual_height, :] = scratchpad

            # Bottom half: Screen
            screen_resized = cv2.resize(screen_frame, (self.width, dual_height))
            mixed_frame[dual_height:dual_height*2, :] = screen_resized

            print("MediaMixer: Mixing scratchpad + screen (2-section layout)")
            return mixed_frame

        # If only screen is available, use full-frame screen for better AI readability
        if screen_frame is not None:
            # Return full-resolution screen only (1920x1920 for better quality)
            return cv2.resize(screen_frame, (self.width, self.width))

        # Fallback to 3-section mix only if no screen available
        mixed_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Section 1: Scratchpad (white if no data)
        if self.scratchpad_frame is not None:
            scratchpad = cv2.resize(self.scratchpad_frame, (self.width, self.section_height))
        else:
            scratchpad = np.ones((self.section_height, self.width, 3), dtype=np.uint8) * 255
        mixed_frame[0:self.section_height, :] = scratchpad

        # Section 2: Screen share (black if disabled)
        if screen_frame is not None:
            mixed_frame[self.section_height:2*self.section_height, :] = screen_frame

        # Section 3: Camera (gray if disabled)
        if camera_frame is not None:
            mixed_frame[2*self.section_height:3*self.section_height, :] = camera_frame
        else:
            mixed_frame[2*self.section_height:3*self.section_height, :] = 64

        return mixed_frame

    def frame_to_base64(self, frame):
        """Convert frame to base64 JPEG"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])  # Higher quality for better text readability
        return base64.b64encode(buffer).decode('utf-8')

    def handle_command(self, data):
        """Handle WebSocket commands"""
        if data.get('type') == 'scratchpad_frame':
            print(f"MediaMixer: Received scratchpad frame, data length: {len(data.get('data', ''))}")
            try:
                base64_data = data['data'].split(',')[1]
                img_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(img_bytes))
                self.scratchpad_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                print(f"MediaMixer: Scratchpad frame processed, size: {self.scratchpad_frame.shape}")
            except Exception as e:
                print(f"MediaMixer: Error processing scratchpad frame: {e}")

        elif data.get('type') == 'toggle_camera':
            enabled = data.get('data', {}).get('enabled', False)
            self.show_camera = enabled
            print(f"Camera toggled: {'ON' if enabled else 'OFF'}")

            if enabled and not self.camera:
                self.init_camera()
            elif not enabled:
                self.release_camera()

        elif data.get('type') == 'toggle_screen':
            enabled = data.get('data', {}).get('enabled', False)
            self.show_screen = enabled
            print(f"Screen share toggled: {'ON' if enabled else 'OFF'}")

        else:
            print(f"Unknown command: {data.get('type')}")

    def stop(self):
        """Clean shutdown"""
        print("Stopping MediaMixer...")
        self.running = False
        self.release_camera()
        cv2.destroyAllWindows()
        print("MediaMixer stopped")


# Global mixer instance shared between both servers
mixer = MediaMixer()

async def handle_command_client(websocket):
    """Handle WebSocket client for commands/input (port 8765)"""
    print(f"Command client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                mixer.handle_command(data)
            except Exception as e:
                print(f"Error processing command: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"Command client {websocket.remote_address} disconnected")


async def handle_video_client(websocket):
    """Handle WebSocket client for video output (port 8766)"""
    print(f"Video client connected: {websocket.remote_address}")
    mixer.running = True

    try:
        while mixer.running:
            try:
                frame = mixer.mix_frames()
                base64_frame = mixer.frame_to_base64(frame)
                await websocket.send(base64_frame)

                # Responsive sleep for quick shutdown
                for _ in range(67):  # 67ms total (15 FPS)
                    if not mixer.running:
                        break
                    await asyncio.sleep(0.001)  # 1ms chunks

            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                print(f"Error sending frames: {e}")
                break
    finally:
        print(f"Video client {websocket.remote_address} disconnected")


async def main():
    """Main server function"""
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        print(f"\nShutting down (signal {signum})...")
        asyncio.get_event_loop().call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    command_server = None
    video_server = None
    try:
        # Start command server (port 8765) - receives commands/frames from frontend
        command_server = await websockets.serve(handle_command_client, "localhost", 8765)
        print("Command WebSocket server started on ws://localhost:8765")

        # Start video server (port 8766) - sends video frames to frontend
        video_server = await websockets.serve(handle_video_client, "localhost", 8766)
        print("Video WebSocket server started on ws://localhost:8766")

        print("Press Ctrl+C to stop")

        await shutdown_event.wait()

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        if command_server:
            command_server.close()
            await command_server.wait_closed()
        if video_server:
            video_server.close()
            await video_server.wait_closed()
        mixer.stop()
        print("Server shutdown complete")


if __name__ == '__main__':
    asyncio.run(main())