import json
import os
import time
import logging
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def calculate_grade_from_age(age: int) -> str:
    """
    Calculate grade level from student age.
    Intelligent mapping (not hardcoded values):
    Age 5 → K
    Age 6 → GRADE_1
    Age 7 → GRADE_2
    ...
    Age 17 → GRADE_12
    Age 18+ → GRADE_12
    """
    if age <= 5:
        return "K"
    elif age >= 18:
        return "GRADE_12"
    else:
        return f"GRADE_{age - 5}"

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
    age: int = 5  # Default kindergarten age
    current_grade: str = "K"  # Calculated from age
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'skill_states': {k: v.to_dict() for k, v in self.skill_states.items()},
            'question_history': [asdict(attempt) for attempt in self.question_history],
            'student_notes': self.student_notes,
            'age': self.age,
            'current_grade': self.current_grade
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
            student_notes=data.get('student_notes', {}),
            age=data.get('age', 5),
            current_grade=data.get('current_grade', 'K')
        )

class UserManager:
    def __init__(self, users_folder: str = "Users", use_mongodb: bool = True):
        self.users_folder = users_folder
        self.use_mongodb = use_mongodb
        self.mongo = None
        
        # Initialize MongoDB if enabled
        if use_mongodb:
            try:
                from managers.mongodb_manager import mongo_db
                self.mongo = mongo_db
                logger.info("[MONGODB] UserManager using MongoDB for user storage")
            except Exception as e:
                logger.error(f"[ERROR] Could not initialize MongoDB for users: {e}")
                raise RuntimeError(f"MongoDB initialization failed: {e}. Please configure MONGODB_URI in .env file.")
    
    def ensure_users_folder_exists(self):
        """Create users folder if it doesn't exist"""
        if not os.path.exists(self.users_folder):
            os.makedirs(self.users_folder)
            logger.info(f"[FOLDER] Created {self.users_folder} folder for user data")
    
    def initialize_skills_for_grade(
        self, 
        current_grade_str: str, 
        all_skills: Dict[str, 'Skill']
    ) -> Dict[str, SkillState]:
        """
        Initialize skill states based on student's current grade (cold-start).
        
        Logic:
        - Skills BELOW current grade: memory_strength = 2.0 (probability ~0.88)
        - Skills AT current grade: memory_strength = 0.0 (probability ~0.50)
        - Skills ABOVE current grade: memory_strength = -2.0 (probability ~0.12)
        
        Using memory_strength values that map to meaningful probabilities via sigmoid.
        """
        from services.DashSystem.dash_system import GradeLevel
        
        try:
            current_grade = GradeLevel[current_grade_str]
        except KeyError:
            logger.warning(f"[COLD_START] Invalid grade '{current_grade_str}', defaulting to K")
            current_grade = GradeLevel.K
        
        skill_states = {}
        below_grade_count = 0
        at_grade_count = 0
        above_grade_count = 0
        
        for skill_id, skill in all_skills.items():
            skill_grade_value = skill.grade_level.value
            current_grade_value = current_grade.value
            
            if skill_grade_value < current_grade_value:
                # Below current grade - assumed mastered
                memory_strength = 2.0  # sigmoid(2.0) ≈ 0.88
                below_grade_count += 1
            elif skill_grade_value == current_grade_value:
                # At current grade - currently learning
                memory_strength = 0.0  # sigmoid(0.0) = 0.50
                at_grade_count += 1
            else:
                # Above current grade - not ready yet
                memory_strength = -2.0  # sigmoid(-2.0) ≈ 0.12
                above_grade_count += 1
            
            skill_states[skill_id] = SkillState(
                memory_strength=memory_strength,
                last_practice_time=None,
                practice_count=0,
                correct_count=0
            )
        
        logger.info(f"[COLD_START] Initialized skills for grade {current_grade_str}:")
        logger.info(f"  Below grade ({current_grade_value}): {below_grade_count} skills at memory_strength=2.0")
        logger.info(f"  At grade ({current_grade_value}): {at_grade_count} skills at memory_strength=0.0")
        logger.info(f"  Above grade ({current_grade_value}): {above_grade_count} skills at memory_strength=-2.0")
        
        return skill_states
    
    def get_user_file_path(self, user_id: str) -> str:
        """Get the file path for a user's JSON file"""
        return os.path.join(self.users_folder, f"{user_id}.json")
    
    def user_exists(self, user_id: str) -> bool:
        """Check if a user file exists"""
        return os.path.exists(self.get_user_file_path(user_id))
    
    def create_new_user(
        self, 
        user_id: str, 
        all_skill_ids: List[str] = None,
        all_skills: Dict = None,
        age: int = 5
    ) -> UserProfile:
        """
        Create a new user with cold-start skill initialization based on age.
        
        Args:
            user_id: Unique identifier for the user
            all_skill_ids: List of all skill IDs (for backward compatibility)
            all_skills: Dictionary of all Skill objects (for cold-start)
            age: Student's age (default: 5 for kindergarten)
        """
        current_time = time.time()
        current_grade = calculate_grade_from_age(age)
        
        # Initialize skills based on grade if all_skills provided
        if all_skills:
            skill_states = self.initialize_skills_for_grade(current_grade, all_skills)
            logger.info(f"[USER] Created new user with cold-start: {user_id} (age {age}, grade {current_grade})")
        else:
            # Fallback to old behavior for backward compatibility
            skill_states = {}
            skill_ids = all_skill_ids or []
            for skill_id in skill_ids:
                skill_states[skill_id] = SkillState(
                    memory_strength=0.0,
                    last_practice_time=None,
                    practice_count=0,
                    correct_count=0
                )
            logger.info(f"[USER] Created new user (legacy mode): {user_id}")
        
        user_profile = UserProfile(
            user_id=user_id,
            created_at=current_time,
            last_updated=current_time,
            skill_states=skill_states,
            question_history=[],
            student_notes={},
            age=age,
            current_grade=current_grade
        )
        
        self.save_user(user_profile)
        return user_profile
    
    def load_user(self, user_id: str) -> Optional[UserProfile]:
        """Load a user profile from MongoDB only"""
        
        if not self.use_mongodb or not self.mongo:
            raise RuntimeError("MongoDB is required. Please configure MONGODB_URI in .env file.")
        
        try:
            data = self.mongo.users.find_one({"user_id": user_id})
            
            if not data:
                return None
            
            # Remove MongoDB _id field
            data.pop('_id', None)
            
            user_profile = UserProfile.from_dict(data)
            logger.info(f"[MONGODB] Loaded user: {user_id} (age: {user_profile.age}, grade: {user_profile.current_grade})")
            return user_profile
            
        except Exception as e:
            logger.error(f"[ERROR] Error loading user {user_id} from MongoDB: {e}")
            raise RuntimeError(f"Failed to load user from MongoDB: {e}. Local fallback disabled.")
    
    def save_user(self, user_profile: UserProfile):
        """Save a user profile to MongoDB only"""
        user_profile.last_updated = time.time()
        
        if not self.use_mongodb or not self.mongo:
            raise RuntimeError("MongoDB is required. Please configure MONGODB_URI in .env file.")
        
        try:
            # Use upsert to create or update
            result = self.mongo.users.update_one(
                {"user_id": user_profile.user_id},
                {"$set": user_profile.to_dict()},
                upsert=True
            )
            # logger.info(f"[MONGODB] Saved user: {user_profile.user_id}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error saving user {user_profile.user_id} to MongoDB: {e}")
            raise RuntimeError(f"Failed to save user to MongoDB: {e}. Local fallback disabled.")
    
    def get_or_create_user(
        self, 
        user_id: str, 
        all_skill_ids: List[str] = None,
        all_skills: Dict = None,
        age: int = None  # Made optional - will use existing age from MongoDB or default to 7
    ) -> UserProfile:
        """Get existing user or create new one with cold-start if doesn't exist"""
        user_profile = self.load_user(user_id)
        
        if user_profile is None:
            # User doesn't exist - create new one
            # Use provided age or default to 7 (Grade 2)
            if age is None:
                age = 7
                logger.info(f"[NEW_USER] Creating user {user_id} with default age: {age}")
            
            user_profile = self.create_new_user(user_id, all_skill_ids, all_skills, age)
        else:
            # User exists - use their existing age from MongoDB
            logger.info(f"[EXISTING_USER] Loaded user {user_id} with age: {user_profile.age}")
            
            # Check if any new skills need to be added (for existing users)
            if all_skill_ids:
                missing_skills = set(all_skill_ids) - set(user_profile.skill_states.keys())
                if missing_skills:
                    for skill_id in missing_skills:
                        user_profile.skill_states[skill_id] = SkillState(
                            memory_strength=0.0,
                            last_practice_time=None,
                            practice_count=0,
                            correct_count=0
                        )
                    logger.info(f"[ADDED] Added {len(missing_skills)} new skills to user {user_id}")
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