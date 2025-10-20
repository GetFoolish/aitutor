# models/question_model.py
from typing import List, Dict, Any, Optional
from beanie import Document
from pydantic import BaseModel


class QuestionDocument(Document):
    question: Dict
    answerArea: Dict[str, Any]
    hints: List 
    itemDataVersion: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    class Settings:
        name = "question"