import websockets
import asyncio
import json
import logging
from typing import Optional
from ..core.context import Event
from .queue_manager import EventQueueManager

logger = logging.getLogger(__name__)


class WebSocketEventHandler:
    def __init__(self, queue_manager: EventQueueManager, server_url: str = "ws://localhost:8767/ta"):
        self.queue_manager = queue_manager
        self.server_url = server_url
        self.ws_connection: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.reconnect_delay = 5
        self.seen_message_ids = set()  # Track seen message IDs for deduplication
        self.last_sequence = {}  # Track last sequence per session
        self.max_seen_ids = 10000  # Prevent memory leak
        self.sequence_gaps = {}  # Track sequence gaps per session

    async def connect(self):
        """Connect to WebSocket server with retry logic"""
        max_retries = None  # Retry indefinitely
        retry_count = 0
        
        while max_retries is None or retry_count < max_retries:
            try:
                self.ws_connection = await websockets.connect(self.server_url)
                self.running = True
                logger.info(f"✅ Connected to server.js WebSocket at {self.server_url}")
                return True
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Failed to connect to WebSocket (attempt {retry_count}): {e}, retrying in {self.reconnect_delay}s")
                await asyncio.sleep(self.reconnect_delay)

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        self.running = False
        if self.ws_connection:
            try:
                await self.ws_connection.close()
                logger.info("🔌 Disconnected from server.js WebSocket")
            except Exception as e:
                logger.warning(f"Error during WebSocket disconnect: {e}")
            finally:
                self.ws_connection = None

    async def listen(self):
        """Listen for messages from WebSocket server"""
        while self.running:
            try:
                # Ensure connection exists before receiving
                if not self.ws_connection:
                    if not self.running:
                        break
                    await self.connect()
                    continue
                
                # Try to receive message (will raise ConnectionClosed if closed)
                message = await self.ws_connection.recv()
                data = json.loads(message)
                
                # Check for duplicates using message_id
                message_id = data.get('message_id')
                if message_id:
                    if message_id in self.seen_message_ids:
                        logger.warning(
                            f"⚠️ Duplicate message detected: {message_id} "
                            f"(type: {data.get('type')}, session: {data.get('data', {}).get('session_id', 'N/A')}), skipping"
                        )
                        continue
                    self.seen_message_ids.add(message_id)
                    # Cleanup old IDs to prevent memory leak
                    if len(self.seen_message_ids) > self.max_seen_ids:
                        # Remove oldest 20% of IDs
                        ids_list = list(self.seen_message_ids)
                        remove_count = len(ids_list) // 5
                        self.seen_message_ids = set(ids_list[remove_count:])
                        logger.debug(f"🧹 Cleaned up {remove_count} old message IDs from deduplication cache")
                
                # Check sequence gaps
                sequence = data.get('sequence')
                session_id = data.get('data', {}).get('session_id')
                if sequence is not None and session_id:
                    last_seq = self.last_sequence.get(session_id)
                    if last_seq is not None:
                        if sequence > last_seq + 1:
                            gap_size = sequence - last_seq - 1
                            gap_count = self.sequence_gaps.get(session_id, 0) + 1
                            self.sequence_gaps[session_id] = gap_count
                            logger.warning(
                                f"⚠️ Sequence gap detected for session {session_id}: "
                                f"expected {last_seq + 1}, got {sequence} (gap: {gap_size} messages, "
                                f"total gaps: {gap_count})"
                            )
                        elif sequence <= last_seq:
                            logger.warning(
                                f"⚠️ Out-of-order message for session {session_id}: "
                                f"expected > {last_seq}, got {sequence}"
                            )
                    self.last_sequence[session_id] = sequence
                
                event = Event.from_websocket(data)
                self.queue_manager.enqueue(event)
                
            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    logger.warning("⚠️ WebSocket connection closed, reconnecting...")
                    self.ws_connection = None
                    # Don't call connect() here - let the loop handle it
                    await asyncio.sleep(1)
                else:
                    break
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse WebSocket message as JSON: {e}")
                logger.debug(f"Raw message: {message if 'message' in locals() else 'N/A'}")
                await asyncio.sleep(0.1)
            except Exception as e:
                if self.running:
                    logger.error(f"❌ Error receiving WebSocket message: {e}", exc_info=True)
                    await asyncio.sleep(1)
                else:
                    break

    async def start(self):
        await self.connect()
        await self.listen()

