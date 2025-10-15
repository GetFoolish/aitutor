from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

class Skill(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(alias="_id")
    name: Optional[str] = None
    learning_path: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    difficulty: Optional[float] = 0.0
    forgetting_rate: Optional[float] = 0.08

class Question(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(alias="_id")
    skill_ids: List[str]
    learning_path: Optional[str] = None
    difficulty_level: Optional[float] = 0.0
    question_type: Optional[str] = None
    tags: Optional[List[str]] = None
    content: Optional[str] = None

class QuestionAttempt(BaseModel):
    question_id: str
    is_correct: bool
    timestamp: float
    response_time_seconds: Optional[float] = None

class SkillState(BaseModel):
    memory_strength: float = 0.0
    last_practice_time: Optional[float] = None
    practice_count: int = 0
    correct_count: int = 0

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(alias="_id")
    skill_states: Dict[str, SkillState] = Field(default_factory=dict)
    question_history: List[QuestionAttempt] = Field(default_factory=list)
