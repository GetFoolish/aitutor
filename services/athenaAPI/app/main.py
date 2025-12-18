"""
SherlockED API New - Athena-based Question Renderer Service

A completely new question fetching and rendering service that replaces
the old Perseus-based implementation. Uses the Athena renderer.

NO CODE FROM SHERLOCKEDAPI OR PERSEUS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add project root to path for shared imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS

from app.routes import router

app = FastAPI(
    title="SherlockED API New",
    description="Athena-based question rendering service. Fetches questions from MongoDB and serves them in Athena format.",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "SherlockED API New",
        "version": "2.0.0",
        "renderer": "Athena",
        "description": "New question service with Athena renderer"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sherlockedAPI_New"}

# Include routes
app.include_router(router, prefix="/api", tags=["questions"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
