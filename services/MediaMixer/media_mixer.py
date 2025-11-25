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
import sys
import time
import uuid
import logging
from typing import Dict, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s|%(levelname)s|%(message)s|file:%(filename)s:line:%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class MediaMixer:
    """MediaMixer - receives all frames from browser"""

    def __init__(self, width=1280, height=2160, fps=15):
        self.width = width
        self.height = height
        self.fps = fps
        self.section_height = height // 3

        # Use full resolution for better text clarity
        self.internal_width = width  # Full resolution
        self.internal_height = height  # Full resolution
        self.internal_section_height = self.internal_height // 3

        # State - all frames come from browser
        self.running = False
        self.show_camera = False
        self.show_screen = False
        self.scratchpad_frame = None
        self.camera_frame = None
        self.screen_frame = None

        logger.info("MediaMixer initialized - waiting for frames from browser")

    def mix_frames(self):
        """Mix all sources into single frame"""
        # Use full resolution for better text clarity
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
        """Convert frame to base64 JPEG with improved quality for text clarity"""
        # Increased quality to 85 for better text readability
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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
                logger.error(f"Error processing scratchpad frame: {e}", exc_info=True)

        elif data.get('type') == 'camera_frame':
            try:
                base64_data = data['data'].split(',')[1] if ',' in data['data'] else data['data']
                img_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(img_bytes))
                self.camera_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.error(f"Error processing camera frame: {e}", exc_info=True)

        elif data.get('type') == 'screen_frame':
            try:
                base64_data = data['data'].split(',')[1] if ',' in data['data'] else data['data']
                img_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(img_bytes))
                self.screen_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.error(f"Error processing screen frame: {e}", exc_info=True)

        elif data.get('type') == 'toggle_camera':
            enabled = data.get('data', {}).get('enabled', False)
            self.show_camera = enabled
            logger.info(f"Camera toggled: {'ON' if enabled else 'OFF'}")

        elif data.get('type') == 'toggle_screen':
            enabled = data.get('data', {}).get('enabled', False)
            self.show_screen = enabled
            logger.info(f"Screen share toggled: {'ON' if enabled else 'OFF'}")

    def stop(self):
        """Clean shutdown"""
        logger.info("Stopping MediaMixer...")
        self.running = False
        logger.info("MediaMixer stopped")


# Session management for multi-tenant support
class SessionManager:
    """Manages multiple MediaMixer instances, one per student session"""
    
    def __init__(self):
        # Map session_id -> MediaMixer instance
        self.sessions: Dict[str, MediaMixer] = {}
        # Map connection -> session_id (for both command and video connections)
        self.connection_to_session: Dict[Any, str] = {}
        # Map session_id -> (command_ws, video_ws, created_at)
        self.session_connections: Dict[str, Tuple[Optional[Any], Optional[Any], float]] = {}
        # Connection pairing window (seconds) - connections from same IP within this window are paired
        self.pairing_window = 5.0
        # Cleanup interval for orphaned sessions
        self.last_cleanup = time.time()
        self.cleanup_interval = 60.0  # Clean up every 60 seconds
        self.session_timeout = 300.0  # Remove sessions inactive for 5 minutes
    
    def _get_client_ip(self, websocket) -> str:
        """Extract client IP address from websocket"""
        try:
            if hasattr(websocket, 'remote_address'):
                if isinstance(websocket.remote_address, tuple):
                    return websocket.remote_address[0]
                return str(websocket.remote_address)
            elif hasattr(websocket, 'request') and hasattr(websocket.request, 'remote_addr'):
                return websocket.request.remote_addr
        except Exception as e:
            logger.warning(f"Could not extract IP address: {e}")
        return "unknown"
    
    def _generate_session_id(self, client_ip: str) -> str:
        """Generate a unique session ID"""
        return f"{client_ip}_{uuid.uuid4().hex[:8]}"
    
    def get_or_create_session(self, websocket, path: str) -> Tuple[str, MediaMixer]:
        """Get or create a session for a connection"""
        client_ip = self._get_client_ip(websocket)
        current_time = time.time()
        
        # Check if this connection already has a session
        if websocket in self.connection_to_session:
            session_id = self.connection_to_session[websocket]
            return session_id, self.sessions[session_id]
        
        # Try to find existing session from same IP within pairing window
        for session_id, (cmd_ws, vid_ws, created_at) in list(self.session_connections.items()):
            if current_time - created_at > self.pairing_window:
                continue
            
            session_ip = session_id.split('_')[0] if '_' in session_id else "unknown"
            if session_ip == client_ip:
                # Found existing session from same IP
                mixer = self.sessions[session_id]
                
                # Check if we can pair this connection
                if path == "/command" and cmd_ws is None:
                    # Pair command connection
                    self.connection_to_session[websocket] = session_id
                    self.session_connections[session_id] = (websocket, vid_ws, created_at)
                    logger.info(f"Paired command connection to existing session {session_id}")
                    return session_id, mixer
                elif path == "/video" and vid_ws is None:
                    # Pair video connection
                    self.connection_to_session[websocket] = session_id
                    self.session_connections[session_id] = (cmd_ws, websocket, created_at)
                    logger.info(f"Paired video connection to existing session {session_id}")
                    return session_id, mixer
        
        # Create new session
        session_id = self._generate_session_id(client_ip)
        mixer = MediaMixer()
        self.sessions[session_id] = mixer
        self.connection_to_session[websocket] = session_id
        
        if path == "/command":
            self.session_connections[session_id] = (websocket, None, current_time)
        elif path == "/video":
            self.session_connections[session_id] = (None, websocket, current_time)
        
        logger.info(f"Created new session {session_id} for {client_ip} on path {path}")
        return session_id, mixer
    
    def remove_connection(self, websocket):
        """Remove a connection and cleanup session if both connections are gone"""
        if websocket not in self.connection_to_session:
            return
        
        session_id = self.connection_to_session[websocket]
        del self.connection_to_session[websocket]
        
        if session_id in self.session_connections:
            cmd_ws, vid_ws, created_at = self.session_connections[session_id]
            
            # Remove this connection from the session
            if cmd_ws == websocket:
                cmd_ws = None
            elif vid_ws == websocket:
                vid_ws = None
            
            # Update session connections
            if cmd_ws is None and vid_ws is None:
                # Both connections closed, cleanup session
                if session_id in self.sessions:
                    self.sessions[session_id].stop()
                    del self.sessions[session_id]
                del self.session_connections[session_id]
                logger.info(f"Cleaned up session {session_id} (both connections closed)")
            else:
                # One connection still active
                self.session_connections[session_id] = (cmd_ws, vid_ws, created_at)
                logger.info(f"Removed connection from session {session_id}, session still active")
    
    def cleanup_orphaned_sessions(self):
        """Remove sessions that have been inactive for too long"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = current_time
        sessions_to_remove = []
        
        for session_id, (cmd_ws, vid_ws, created_at) in list(self.session_connections.items()):
            # Check if session is orphaned (no active connections and old)
            if cmd_ws is None and vid_ws is None:
                if current_time - created_at > self.session_timeout:
                    sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            if session_id in self.sessions:
                self.sessions[session_id].stop()
                del self.sessions[session_id]
            del self.session_connections[session_id]
            logger.info(f"Cleaned up orphaned session {session_id}")


# Global session manager
session_manager = SessionManager()


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
            logger.warning(f"Could not determine path: {e}")
            path = '/'
    
    # Default fallback
    if path is None:
        path = '/'
    
    # Get or create session for this connection
    session_id, mixer = session_manager.get_or_create_session(websocket, path)
    logger.info(f"Client connected from {websocket.remote_address} on path {path} (session: {session_id})")

    if path == "/command":
        # Command connection - receives frames and commands
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    mixer.handle_command(data)
                except Exception as e:
                    logger.error(f"Error processing command: {e}", exc_info=True)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            logger.info(f"Command client disconnected (session: {session_id})")
            session_manager.remove_connection(websocket)

    elif path == "/video":
        # Video connection - sends mixed frames
        mixer.running = True
        try:
            # Reduce frame rate to 10 FPS for better performance (was 15)
            frame_delay = 1 / 10
            while mixer.running:
                try:
                    # Periodic cleanup of orphaned sessions
                    session_manager.cleanup_orphaned_sessions()
                    
                    frame = mixer.mix_frames()
                    base64_frame = mixer.frame_to_base64(frame)
                    await websocket.send(base64_frame)

                    # 10 FPS for better network performance
                    await asyncio.sleep(frame_delay)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"Video WebSocket connection closed during send (session: {session_id})")
                    break
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info(f"Video WebSocket connection closed normally (session: {session_id})")
                    break
                except websockets.exceptions.ConnectionClosedError:
                    logger.error(f"Video WebSocket connection closed with error (session: {session_id})")
                    break
                except Exception as e:
                    logger.error(f"Error sending frames (session: {session_id}): {e}", exc_info=True)
                    # Continue the loop instead of breaking to keep connection alive
                    # Only break on connection errors, not processing errors
                    await asyncio.sleep(frame_delay)
                    continue
        finally:
            # Reset running state when video connection closes
            # Only reset if this connection was the one running it
            if mixer.running:
                mixer.running = False
            logger.info(f"Video client disconnected (session: {session_id})")
            session_manager.remove_connection(websocket)
    else:
        logger.warning(f"Unknown path: {path}")


async def main():
    """Main server function"""
    # Get port from environment (Cloud Run uses PORT env var)
    port = int(os.environ.get('PORT', 8765))  # 8765 for local, 8080 for cloud

    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"Shutting down (signal {signum})...")
        asyncio.get_event_loop().call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server = None
    try:
        # Single WebSocket server with path-based routing
        server = await websockets.serve(handle_websocket, "0.0.0.0", port)
        logger.info(f"MediaMixer WebSocket server started on port {port}")
        logger.info("  - Command endpoint: /command")
        logger.info("  - Video endpoint: /video")
        logger.info("Waiting for connections...")

        await shutdown_event.wait()

    except Exception as e:
        logger.critical(f"Server error: {e}", exc_info=True)
    finally:
        if server:
            server.close()
            await server.wait_closed()
        # Stop all active mixers
        for session_id, mixer in list(session_manager.sessions.items()):
            mixer.stop()
        session_manager.sessions.clear()
        session_manager.connection_to_session.clear()
        session_manager.session_connections.clear()
        logger.info("Server shutdown complete")


if __name__ == '__main__':
    asyncio.run(main())
