import os
import sys
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from services.TeachingAssistant.teaching_assistant import TeachingAssistant

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ta_instance: TeachingAssistant = None
background_task: asyncio.Task = None

port = 8002
PORT = int(os.getenv("PORT", str(port)))
HOST = os.getenv("HOST", "0.0.0.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ta_instance, background_task
    
    server_url = os.getenv("TUTOR_WS_URL", "ws://localhost:8767/ta")
    tutor_server_url = os.getenv("TUTOR_SERVER_URL", "http://localhost:8767")
    
    ta_instance = TeachingAssistant(
        server_url=server_url,
        tutor_server_url=tutor_server_url
    )
    
    background_task = asyncio.create_task(ta_instance.run())
    logger.info("TeachingAssistant started")
    
    yield
    
    logger.info("Shutting down TeachingAssistant...")
    await ta_instance.stop()
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    logger.info("TeachingAssistant stopped")


app = FastAPI(
    title="TeachingAssistant API",
    description="AI Tutor Teaching Assistant Service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TeachingAssistant",
        "websocket_connected": ta_instance.event_handler.running if ta_instance else False
    }


@app.get("/")
async def root():
    return {
        "service": "TeachingAssistant API",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )

