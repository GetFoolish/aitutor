#!/usr/bin/env python3
"""
MediaMixer - Cloud Run Compatible Version
Combines camera, screen share, and scratchpad streams
"""

import cv2
import numpy as np
from PIL import Image
import base64
import io
import asyncio
import websockets
import signal
import json
import os


class MediaMixer:
    """MediaMixer - receives all frames from browser"""

    def __init__(self, width=1280, height=2160, fps=15):
        self.width = width
        self.height = height
        self.fps = fps
        self.section_height = height // 3

        # Performance optimization: use smaller internal resolution
        self.internal_width = 640  # Half resolution
        self.internal_height = 1080  # Half resolution
        self.internal_section_height = self.internal_height // 3

        # State - all frames come from browser
        self.running = False
        self.show_camera = False
        self.show_screen = False
        self.scratchpad_frame = None
        self.camera_frame = None
        self.screen_frame = None

        print("MediaMixer initialized - waiting for frames from browser")

    def mix_frames(self):
        """Mix all sources into single frame"""
        # Use smaller internal resolution for better performance
        mixed_frame = np.zeros((self.internal_height, self.internal_width, 3), dtype=np.uint8)

        # Section 1: Scratchpad (white if no data)
        if self.scratchpad_frame is not None:
            scratchpad = cv2.resize(self.scratchpad_frame, (self.internal_width, self.internal_section_height))
        else:
            scratchpad = np.ones((self.internal_section_height, self.internal_width, 3), dtype=np.uint8) * 255
        mixed_frame[0:self.internal_section_height, :] = scratchpad

        # Section 2: Screen share (black if disabled)
        if self.show_screen and self.screen_frame is not None:
            screen = cv2.resize(self.screen_frame, (self.internal_width, self.internal_section_height))
            mixed_frame[self.internal_section_height:2*self.internal_section_height, :] = screen
        else:
            mixed_frame[self.internal_section_height:2*self.internal_section_height, :] = 0

        # Section 3: Camera (gray if disabled)
        if self.show_camera and self.camera_frame is not None:
            camera = cv2.resize(self.camera_frame, (self.internal_width, self.internal_section_height))
            mixed_frame[2*self.internal_section_height:3*self.internal_section_height, :] = camera
        else:
            mixed_frame[2*self.internal_section_height:3*self.internal_section_height, :] = 64

        return mixed_frame

    def frame_to_base64(self, frame):
        """Convert frame to base64 JPEG with lower quality for performance"""
        # Reduce quality to 60 for better performance (was 80)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return base64.b64encode(buffer).decode('utf-8')

    def handle_command(self, data):
        """Handle WebSocket commands"""
        if data.get('type') == 'scratchpad_frame':
            try:
                base64_data = data['data'].split(',')[1]
                img_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(img_bytes))
                self.scratchpad_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error processing scratchpad frame: {e}")

        elif data.get('type') == 'camera_frame':
            try:
                base64_data = data['data'].split(',')[1] if ',' in data['data'] else data['data']
                img_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(img_bytes))
                self.camera_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error processing camera frame: {e}")

        elif data.get('type') == 'screen_frame':
            try:
                base64_data = data['data'].split(',')[1] if ',' in data['data'] else data['data']
                img_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(img_bytes))
                self.screen_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error processing screen frame: {e}")

        elif data.get('type') == 'toggle_camera':
            enabled = data.get('data', {}).get('enabled', False)
            self.show_camera = enabled
            print(f"Camera toggled: {'ON' if enabled else 'OFF'}")

        elif data.get('type') == 'toggle_screen':
            enabled = data.get('data', {}).get('enabled', False)
            self.show_screen = enabled
            print(f"Screen share toggled: {'ON' if enabled else 'OFF'}")

    def stop(self):
        """Clean shutdown"""
        print("Stopping MediaMixer...")
        self.running = False
        print("MediaMixer stopped")


# Global mixer instance
mixer = MediaMixer()


async def handle_websocket(websocket, *args):
    """Handle WebSocket connections - compatible with different websockets versions"""
    # Extract path from arguments or websocket object
    # websockets library may pass path as second argument or we need to extract it
    path = None
    
    # Try to get path from arguments first
    if args and len(args) > 0:
        path = args[0]
    
    # If not in arguments, try to get from websocket object
    if path is None:
        try:
            # Try different ways to access the path
            if hasattr(websocket, 'path'):
                path = websocket.path
            elif hasattr(websocket, 'request') and hasattr(websocket.request, 'path'):
                path = websocket.request.path
            elif hasattr(websocket, 'request_headers'):
                # Try to extract from request line in headers
                path = getattr(websocket, 'path', '/')
        except Exception as e:
            print(f"Warning: Could not determine path: {e}")
            path = '/'
    
    # Default fallback
    if path is None:
        path = '/'
    
    print(f"Client connected from {websocket.remote_address} on path {path}")

    if path == "/command":
        # Command connection - receives frames and commands
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
            print(f"Command client disconnected")

    elif path == "/video":
        # Video connection - sends mixed frames
        mixer.running = True
        try:
            # Reduce frame rate to 10 FPS for better performance (was 15)
            frame_delay = 1 / 10
            while mixer.running:
                try:
                    frame = mixer.mix_frames()
                    base64_frame = mixer.frame_to_base64(frame)
                    await websocket.send(base64_frame)

                    # 10 FPS for better network performance
                    await asyncio.sleep(frame_delay)

                except websockets.exceptions.ConnectionClosed:
                    print("Video WebSocket connection closed during send")
                    break
                except websockets.exceptions.ConnectionClosedOK:
                    print("Video WebSocket connection closed normally")
                    break
                except websockets.exceptions.ConnectionClosedError:
                    print("Video WebSocket connection closed with error")
                    break
                except Exception as e:
                    print(f"Error sending frames: {e}")
                    import traceback
                    traceback.print_exc()
                    break
        finally:
            # Reset running state when video connection closes
            # Only reset if this connection was the one running it
            if mixer.running:
                mixer.running = False
            print(f"Video client disconnected")
    else:
        print(f"Unknown path: {path}")


async def main():
    """Main server function"""
    # Get port from environment (Cloud Run uses PORT env var)
    port = int(os.environ.get('PORT', 8765))  # 8765 for local, 8080 for cloud

    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        print(f"\nShutting down (signal {signum})...")
        asyncio.get_event_loop().call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server = None
    try:
        # Single WebSocket server with path-based routing
        server = await websockets.serve(handle_websocket, "0.0.0.0", port)
        print(f"MediaMixer WebSocket server started on port {port}")
        print(f"  - Command endpoint: /command")
        print(f"  - Video endpoint: /video")
        print("Waiting for connections...")

        await shutdown_event.wait()

    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if server:
            server.close()
            await server.wait_closed()
        mixer.stop()
        print("Server shutdown complete")


if __name__ == '__main__':
    asyncio.run(main())
