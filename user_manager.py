import json
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

from db.mongo_client import ping_database
from db.user_repository import get_user as mongo_get_user, upsert_user as mongo_upsert_user

@dataclass
class QuestionAttempt:
    question_id: str
    skill_ids: List[str]
    is_correct: bool
    response_time_seconds: float
    timestamp: float
    time_penalty_applied: bool = False

@dataclass
class SkillState:
    memory_strength: float
    last_practice_time: Optional[float]
    practice_count: int
    correct_count: int
    
    def to_dict(self):
        return {
            'memory_strength': self.memory_strength,
            'last_practice_time': self.last_practice_time,
            'practice_count': self.practice_count,
            'correct_count': self.correct_count
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            memory_strength=data['memory_strength'],
            last_practice_time=data['last_practice_time'],
            practice_count=data['practice_count'],
            correct_count=data['correct_count']
        )

@dataclass
class UserProfile:
    user_id: str
    created_at: float
    last_updated: float
    skill_states: Dict[str, SkillState]
    question_history: List[QuestionAttempt]
    student_notes: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'skill_states': {k: v.to_dict() for k, v in self.skill_states.items()},
            'question_history': [asdict(attempt) for attempt in self.question_history],
            'student_notes': self.student_notes
        }
    
    @classmethod
    def from_dict(cls, data):
        skill_states = {k: SkillState.from_dict(v) for k, v in data['skill_states'].items()}
        question_history = [QuestionAttempt(**attempt) for attempt in data['question_history']]
        
        return cls(
            user_id=data['user_id'],
            created_at=data['created_at'],
            last_updated=data['last_updated'],
            skill_states=skill_states,
            question_history=question_history,
            student_notes=data.get('student_notes', {})
        )

class UserManager:
    def __init__(self, users_folder: str = "Users", use_mongo: bool = True):
        self.users_folder = users_folder
        self.use_mongo = use_mongo and ping_database()
        if self.use_mongo:
            print("✅ UserManager configured to use MongoDB.")
        else:
            self.ensure_users_folder_exists()
    
    def ensure_users_folder_exists(self):
        """Create users folder if it doesn't exist"""
        if self.use_mongo:
            return
        if not os.path.exists(self.users_folder):
            os.makedirs(self.users_folder)
            print(f"📁 Created {self.users_folder} folder for user data")
    
    def get_user_file_path(self, user_id: str) -> str:
        """Get the file path for a user's JSON file"""
        return os.path.join(self.users_folder, f"{user_id}.json")
    
    def user_exists(self, user_id: str) -> bool:
        """Check if a user file exists"""
        if self.use_mongo:
            return mongo_get_user(user_id) is not None
        return os.path.exists(self.get_user_file_path(user_id))
    
    def create_new_user(self, user_id: str, all_skill_ids: List[str]) -> UserProfile:
        """Create a new user with empty skill states"""
        current_time = time.time()
        
        # Initialize all skills with default states
        skill_states = {}
        for skill_id in all_skill_ids:
            skill_states[skill_id] = SkillState(
                memory_strength=0.0,
                last_practice_time=None,
                practice_count=0,
                correct_count=0
            )
        
        user_profile = UserProfile(
            user_id=user_id,
            created_at=current_time,
            last_updated=current_time,
            skill_states=skill_states,
            question_history=[],
            student_notes={}
        )
        
        self.save_user(user_profile)
        print(f"👤 Created new user profile: {user_id}")
        return user_profile
    
    def load_user(self, user_id: str) -> Optional[UserProfile]:
        """Load a user profile from JSON file"""
        if self.use_mongo:
            document = mongo_get_user(user_id)
            if not document:
                return None
            try:
                user_profile = UserProfile.from_dict(document)
                print(f"📂 Loaded user profile from MongoDB: {user_id}")
                return user_profile
            except (KeyError, TypeError) as exc:
                print(f"❌ Error parsing MongoDB user {user_id}: {exc}")
                return None

        file_path = self.get_user_file_path(user_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            user_profile = UserProfile.from_dict(data)
            print(f"📂 Loaded user profile: {user_id}")
            return user_profile
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"❌ Error loading user {user_id}: {e}")
            return None
    
    def save_user(self, user_profile: UserProfile):
        """Save a user profile to JSON file"""
        user_profile.last_updated = time.time()
        payload = user_profile.to_dict()

        if self.use_mongo:
            try:
                mongo_upsert_user(user_profile.user_id, payload)
                print(f"💾 Saved user profile to MongoDB: {user_profile.user_id}")
            except Exception as exc:
                print(f"❌ Error saving user {user_profile.user_id} to MongoDB: {exc}")
            return

        file_path = self.get_user_file_path(user_profile.user_id)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(payload, f, indent=2)
            
            print(f"💾 Saved user profile: {user_profile.user_id}")
            
        except Exception as e:
            print(f"❌ Error saving user {user_profile.user_id}: {e}")
    
    def get_or_create_user(self, user_id: str, all_skill_ids: List[str]) -> UserProfile:
        """Get existing user or create new one if doesn't exist"""
        user_profile = self.load_user(user_id)
        
        if user_profile is None:
            user_profile = self.create_new_user(user_id, all_skill_ids)
        else:
            # Check if any new skills need to be added
            missing_skills = set(all_skill_ids) - set(user_profile.skill_states.keys())
            if missing_skills:
                for skill_id in missing_skills:
                    user_profile.skill_states[skill_id] = SkillState(
                        memory_strength=0.0,
                        last_practice_time=None,
                        practice_count=0,
                        correct_count=0
                    )
                print(f"➕ Added {len(missing_skills)} new skills to user {user_id}")
                self.save_user(user_profile)
        
        return user_profile
    
    def add_question_attempt(self, user_profile: UserProfile, question_id: str, 
                           skill_ids: List[str], is_correct: bool, 
                           response_time_seconds: float, time_penalty_applied: bool = False):
        """Add a question attempt to user's history"""
        attempt = QuestionAttempt(
            question_id=question_id,
            skill_ids=skill_ids,
            is_correct=is_correct,
            response_time_seconds=response_time_seconds,
            timestamp=time.time(),
            time_penalty_applied=time_penalty_applied
        )
        
        user_profile.question_history.append(attempt)
        self.save_user(user_profile)
    
    def get_user_stats(self, user_profile: UserProfile) -> Dict:
        """Get summary statistics for a user"""
        total_questions = len(user_profile.question_history)
        correct_answers = sum(1 for attempt in user_profile.question_history if attempt.is_correct)
        
        if total_questions == 0:
            return {
                'total_questions': 0,
                'correct_answers': 0,
                'accuracy': 0.0,
                'avg_response_time': 0.0,
                'time_penalties': 0,
                'skills_practiced': 0
            }
        
        avg_response_time = sum(attempt.response_time_seconds for attempt in user_profile.question_history) / total_questions
        time_penalties = sum(1 for attempt in user_profile.question_history if attempt.time_penalty_applied)
        skills_practiced = len([skill_id for skill_id, state in user_profile.skill_states.items() if state.practice_count > 0])
        
        return {
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'accuracy': correct_answers / total_questions,
            'avg_response_time': avg_response_time,
            'time_penalties': time_penalties,
            'skills_practiced': skills_practiced
        }
    
    def list_all_users(self) -> List[str]:
        """Get list of all user IDs"""
        if not os.path.exists(self.users_folder):
            return []
        
        user_files = [f for f in os.listdir(self.users_folder) if f.endswith('.json')]
        return [f[:-5] for f in user_files]  # Remove .json extension
