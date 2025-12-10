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

    async def connect(self):
        while True:
            try:
                self.ws_connection = await websockets.connect(self.server_url)
                self.running = True
                logger.info("Connected to server.js WebSocket")
                return True
            except Exception as e:
                logger.error(f"Failed to connect: {e}, retrying in {self.reconnect_delay}s")
                await asyncio.sleep(self.reconnect_delay)

    async def disconnect(self):
        self.running = False
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None

    async def listen(self):
        while self.running:
            try:
                if not self.ws_connection or not self.running:
                    await self.connect()
                
                message = await self.ws_connection.recv()
                data = json.loads(message)
                event = Event.from_websocket(data)
                self.queue_manager.enqueue(event)
            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    logger.warning("WebSocket connection closed, reconnecting...")
                    self.running = False
                    await self.connect()
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving message: {e}")
                    await asyncio.sleep(1)

    async def start(self):
        await self.connect()
        await self.listen()

