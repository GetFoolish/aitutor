from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import routes as app_routes
import os
import sys

# Add project root to path for shared imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS

app = FastAPI(
    title="Exam System API",
    description="API for managing exam sessions, user responses, and scoring",
    version="1.0.0"
)

# Configure CORS with secure origins from environment
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
    return {"message": "Exam System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

app.include_router(app_routes.router, prefix="/api", tags=["api"])