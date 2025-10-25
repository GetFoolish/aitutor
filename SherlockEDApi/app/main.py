from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import routes as app_routes 
from beanie import init_beanie 
from motor.motor_asyncio import AsyncIOMotorClient 
from contextlib import asynccontextmanager
from app.database.models import QuestionDocument 
from app.utils.database import seed_db
from app.database.models import QuestionDocument  


async def is_database_empty():
    count = await QuestionDocument.find().count()
    if count > 0:
        return False
    return True 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["question_db"]
    await init_beanie(database=db, document_models=[QuestionDocument])
    if await is_database_empty():    
        print("Seeding database...")
        await seed_db()
    yield
    print("Shutting down...")

app = FastAPI(
    title="Exam System API", 
    description="API for managing exam sessions, user responses, and scoring",
    version="1.0.0",
    lifespan=lifespan
)


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