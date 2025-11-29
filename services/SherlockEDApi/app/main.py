from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import routes as app_routes
import os
import uvicorn

app = FastAPI(
    title="Exam System API",
    description="API for managing exam sessions, user responses, and scoring",
    version="1.0.0"
)

# Configure CORS - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],  # Includes OPTIONS for preflight
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Exam System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

app.include_router(app_routes.router, prefix="/api", tags=["api"])