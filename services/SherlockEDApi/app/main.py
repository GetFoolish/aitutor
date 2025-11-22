from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import routes as app_routes
import uvicorn

app = FastAPI(
    title="Exam System API",
    description="API for managing exam sessions, user responses, and scoring",
    version="1.0.0"
)

origins = [
        "http://localhost",
        "http://localhost:3000", 
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Exam System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

app.include_router(app_routes.router, prefix="/api", tags=["api"])