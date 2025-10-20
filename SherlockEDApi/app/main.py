from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import routes as app_routes 
from contextlib import asynccontextmanager 
from beanie import init_beanie 
from motor.motor_asyncio import AsyncIOMotorClient
from app.database.models import QuestionDocument 
from pydantic import ValidationError, BaseModel
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    print("Starting up...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["questions_db"]
    await init_beanie(database=db, document_models=[QuestionDocument])
    yield
    # Shutdown code
    print("Shutting down...")

app = FastAPI(
    title="Exam System API", 
    description="API for managing exam sessions, user responses, and scoring",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi import FastAPI, Request, HTTPException
import json

@app.post("/test-questions")
async def create_question(request: Request):
    try:
        # Parse the JSON data from the request body
        question_data = await request.json()
        
        # Create the document
        question_doc = QuestionDocument(**question_data)
        await question_doc.insert()
        
        return {"message": "Question stored successfully", "id": str(question_doc.id)}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Exam System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}


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


app.include_router(app_routes.router, prefix="/api", tags=["api"])