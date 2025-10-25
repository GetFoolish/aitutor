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
    created_at: datetime = datetime.now()

    class Settings:
        name = "questions-generated"