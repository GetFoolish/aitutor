from beanie import Document, Link
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import Field, ConfigDict

class QuestionDocument(Document):
    answerArea: Optional[Dict] = None
    hints: Optional[List] = None
    itemDataVersion: Optional[Dict] = None
    question: Dict 
    source: str = "khan"
    generated_count: int = 0
    generated: List[Link["GeneratedQuestionDocument"]] = []
    created_at: datetime = datetime.now()

    class Settings:
        name = "questions" 

class GeneratedQuestionDocument(Document):
    answerArea: Optional[Dict] = None
    hints: Optional[List] = None
    itemDataVersion: Optional[Dict] = None
    question: Dict 
    source: str = "aitutor"
    human_approved: bool = False
    created_at: datetime = datetime.now()
    # Cost tracking fields
    generation_cost: Optional[float] = None  # Total cost in USD
    cost_breakdown: Optional[Dict] = None  # Detailed breakdown by agent/step
    tokens_used: Optional[Dict] = None  # Token usage breakdown

    class Settings:
        name = "questions-generated"

        