#!/usr/bin/env python3
"""
Standalone WebSocket server for synchronizing questions between pipeline and frontend.
This server should run independently alongside the Pipecat pipeline.
"""

import asyncio
import websockets
import json
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global set to track connected frontend clients
frontend_clients = set()


async def broadcast_question_update(question_data: dict):
    """Broadcast question update to all connected frontend clients"""
    if not question_data:
        return

    message = json.dumps({
        "type": "question_update",
        "question_id": question_data.get("question_id"),
        "question_data": question_data
    })

    # Send to all connected clients
    disconnected_clients = set()
    for client in frontend_clients:
        try:
            await client.send(message)
            logger.info(f"Broadcasted question {question_data.get('question_id')} to frontend")
        except Exception as e:
            logger.error(f"Error broadcasting to frontend client: {e}")
            disconnected_clients.add(client)

    # Remove disconnected clients
    frontend_clients.difference_update(disconnected_clients)


async def handle_frontend_client(websocket):
    """Handle a frontend client connection"""
    frontend_clients.add(websocket)
    logger.info(f"Frontend client connected for question sync. Total clients: {len(frontend_clients)}")

    try:
        async for message in websocket:
            # Frontend might send ping/pong or other messages
            logger.debug(f"Received message from frontend: {message}")
    except Exception as e:
        logger.error(f"Frontend client error: {e}")
    finally:
        frontend_clients.remove(websocket)
        logger.info(f"Frontend client disconnected. Total clients: {len(frontend_clients)}")


async def handle_pipeline_client(websocket):
    """Handle pipeline client connection - receives question updates from pipeline"""
    logger.info(f"Pipeline client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "question_update":
                    # Broadcast to all frontend clients
                    await broadcast_question_update(data.get("question_data"))
            except Exception as e:
                logger.error(f"Error processing pipeline message: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        logger.info(f"Pipeline client {websocket.remote_address} disconnected")


async def main():
    """Start both WebSocket servers"""
    # Server for frontend clients (port 8767)
    frontend_port = int(os.getenv("FRONTEND_SYNC_PORT", "8767"))
    logger.info(f"Starting frontend sync WebSocket server on port {frontend_port}")

    # Server for pipeline updates (port 8768)
    pipeline_port = int(os.getenv("PIPELINE_SYNC_PORT", "8768"))
    logger.info(f"Starting pipeline sync WebSocket server on port {pipeline_port}")

    async with websockets.serve(handle_frontend_client, "localhost", frontend_port):
        async with websockets.serve(handle_pipeline_client, "localhost", pipeline_port):
            logger.info("Question sync servers running...")
            logger.info(f"  - Frontend clients connect to: ws://localhost:{frontend_port}")
            logger.info(f"  - Pipeline connects to: ws://localhost:{pipeline_port}")
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Question sync server stopped")
