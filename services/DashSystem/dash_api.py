import time
import sys
import os
import json
import glob
import random
import logging
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.DashSystem.dash_system import DASHSystem, Question

app = FastAPI()
dash_system = DASHSystem()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows the React frontend to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Perseus item model matching frontend expectations
class PerseusQuestion(BaseModel):
    question: dict = Field(description="The question data")
    answerArea: dict = Field(description="The answer area")
    hints: List = Field(description="List of question hints")
    dash_metadata: Optional[dict] = Field(default=None, description="DASH metadata for tracking")
    
    class Config:
        extra = "allow"  # Allow additional fields that aren't in the model

# Path to CurriculumBuilder with full Perseus items
CURRICULUM_BUILDER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'SherlockEDApi', 'CurriculumBuilder')
)

# Skill to Perseus slug prefix mapping
SKILL_TO_SLUG_PREFIX = {
    # Kindergarten
    "counting_1_10": "1.1.1.1",
    "number_recognition": "1.1.1.2",
    "basic_shapes": "1.1.1.3",
    "counting_100": "1.1.1.4",
    # Grade 1
    "addition_basic": "1.1.2.1",
    "subtraction_basic": "1.1.2.2",
    "place_value": "1.1.3.1",
    "skip_counting": "1.1.4.1",
    # Grade 2
    "addition_2digit": "2.1.4.2",
    "subtraction_2digit": "2.1.5.1",
    "multiplication_intro": "2.1.6.1",  # Introduction to Multiplication
    # Grade 3
    "multiplication_basic": "2.1.6.1",
    "multiplication_tables": "2.1.6.1",  # Added missing mapping!
    "division_basic": "2.1.8.1",
    "fractions_intro": "3.1.1.1",
    # Grade 4+
    "fractions_operations": "4.1.1.1",
    "decimals_intro": "4.1.2.1",
    "decimals_operations": "5.1.1.1",
    "percentages": "5.1.2.1",
    "integers": "6.1.1.1",
    "ratios_proportions": "6.1.2.1",
    "algebraic_expressions": "7.1.1.1",
    "linear_equations_1var": "7.1.2.1",
    "linear_equations_2var": "8.1.1.1",
    "quadratic_intro": "8.1.2.1",
    "quadratic_equations": "9.1.1.1",
    "polynomial_operations": "9.1.2.1",
    "geometric_proofs": "10.1.1.1",
    "trigonometry_basic": "10.1.2.1",
    "exponentials_logs": "11.1.1.1",
    "trigonometry_advanced": "11.1.2.1",
    "limits": "12.1.1.1",
    "derivatives": "12.1.2.1",
}

def extract_slug_from_filename(filepath: str) -> str:
    """Extract slug like '1.1.1.1.5' from '1.1.1.1.5_xABC.json'"""
    filename = os.path.basename(filepath)
    slug = filename.split('_')[0]
    return slug

def get_perseus_files_for_skill(skill_id: str, curriculum_path: str) -> List[str]:
    """Get all Perseus files matching a skill's slug prefix"""
    prefix = SKILL_TO_SLUG_PREFIX.get(skill_id, "1.1.1")
    pattern = os.path.join(curriculum_path, f"{prefix}*.json")
    return glob.glob(pattern)

def load_perseus_items_for_dash_questions_from_mongodb(
    dash_questions: List[Question]
) -> List[Dict]:
    """Load Perseus items from MongoDB matching DASH-selected questions"""
    from managers.mongodb_manager import mongo_db
    perseus_items = []
    
    for dash_q in dash_questions:
        skill_id = dash_q.skill_ids[0] if dash_q.skill_ids else "counting_1_10"
        
        # Map skill to Perseus prefix
        prefix = SKILL_TO_SLUG_PREFIX.get(skill_id, "1.1.1")
        
        # Query MongoDB for matching Perseus questions
        try:
            matching_docs = list(mongo_db.perseus_questions.find({
                "skill_prefix": prefix
            }).limit(20))
            
            if not matching_docs:
                # Fallback to any question with similar prefix
                prefix_parts = prefix.split('.')
                broader_prefix = '.'.join(prefix_parts[:3]) if len(prefix_parts) >= 3 else prefix
                matching_docs = list(mongo_db.perseus_questions.find({
                    "skill_prefix": {"$regex": f"^{broader_prefix}"}
                }).limit(20))
            
            if not matching_docs:
                logger.warning(f"No Perseus questions found in MongoDB for skill {skill_id}")
                continue
            
            # Randomly select one
            selected_doc = random.choice(matching_docs)
            
            # Build Perseus data structure
            perseus_data = {
                "question": selected_doc.get("question", {}),
                "answerArea": selected_doc.get("answerArea", {}),
                "hints": selected_doc.get("hints", []),
                "itemDataVersion": selected_doc.get("itemDataVersion", {}),
                "dash_metadata": {
                    'dash_question_id': dash_q.question_id,
                    'skill_ids': dash_q.skill_ids,
                    'difficulty': dash_q.difficulty,
                    'expected_time_seconds': dash_q.expected_time_seconds,
                    'slug': selected_doc.get("slug"),
                    'skill_names': [dash_system.skills[sid].name for sid in dash_q.skill_ids 
                                   if sid in dash_system.skills]
                }
            }
            
            perseus_items.append(perseus_data)
            
        except Exception as e:
            logger.warning(f"Failed to load Perseus from MongoDB for skill {skill_id}: {e}")
    
    return perseus_items

def load_perseus_items_for_dash_questions(
    dash_questions: List[Question],
    curriculum_path: str
) -> List[Dict]:
    """Load Perseus items matching DASH-selected questions (LOCAL FILES FALLBACK)"""
    perseus_items = []
    
    for dash_q in dash_questions:
        skill_id = dash_q.skill_ids[0] if dash_q.skill_ids else "counting_1_10"
        
        # Get matching Perseus files
        matching_files = get_perseus_files_for_skill(skill_id, curriculum_path)
        
        if not matching_files:
            # Fallback to any file if no match
            matching_files = glob.glob(os.path.join(curriculum_path, "1.1.*.json"))
            if not matching_files:
                matching_files = glob.glob(os.path.join(curriculum_path, "*.json"))
        
        if not matching_files:
            logger.warning(f"No Perseus files found for skill {skill_id}")
            continue
            
        # Pick one randomly from matches
        selected_file = random.choice(matching_files[:min(20, len(matching_files))])
        
        try:
            with open(selected_file, 'r', encoding='utf-8') as f:
                perseus_data = json.load(f)
            
            # Tag with DASH metadata
            perseus_data['dash_metadata'] = {
                'dash_question_id': dash_q.question_id,
                'skill_ids': dash_q.skill_ids,
                'difficulty': dash_q.difficulty,
                'expected_time_seconds': dash_q.expected_time_seconds,
                'slug': extract_slug_from_filename(selected_file),
                'skill_names': [dash_system.skills[sid].name for sid in dash_q.skill_ids 
                               if sid in dash_system.skills]
            }
            
            perseus_items.append(perseus_data)
        except Exception as e:
            logger.warning(f"Failed to load Perseus file {selected_file}: {e}")
    
    return perseus_items

def load_perseus_items_from_dir(directory: str, limit: Optional[int] = None) -> List[Dict]:
    """Load Perseus items from CurriculumBuilder directory (legacy function)"""
    all_items = []
    file_pattern = os.path.join(directory, "*.json")
    
    for file_path in glob.glob(file_pattern):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure it has the expected structure
                if isinstance(data, dict) and "question" in data:
                    all_items.append(data)
        except Exception as e:
            logger.warning(f"Warning: Failed to load {file_path}: {e}")
    
    if limit and len(all_items) > limit:
        return random.sample(all_items, limit)
    return all_items

@app.get("/api/questions/{sample_size}", response_model=List[PerseusQuestion])
def get_questions_with_dash_intelligence(sample_size: int, user_id: str = "default_user"):
    """
    Gets questions using DASH intelligence but returns full Perseus items.
    Uses DASH to intelligently select questions based on learning journey and adaptive difficulty.
    
    Args:
        sample_size: Number of questions to return
        user_id: Unique identifier for the user (age fetched from MongoDB)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"[NEW_SESSION] Requesting {sample_size} questions for user: {user_id}")
    logger.info(f"{'='*80}\n")
    
    # Ensure the user exists and is loaded (age comes from MongoDB)
    user_profile = dash_system.load_user_or_create(user_id)
    
    # Use DASH intelligence with flexible selection to get ALL questions
    current_time = time.time()
    selected_questions = []
    selected_question_ids = []  # Track selected question IDs to avoid duplicates
    
    # Get multiple questions using DASH flexible intelligence
    for i in range(sample_size):
        # Use flexible selection that expands to grade-appropriate skills when needed
        next_question = dash_system.get_next_question_flexible(
            user_id, 
            current_time, 
            exclude_question_ids=selected_question_ids
        )
        if next_question:
            selected_questions.append(next_question)
            selected_question_ids.append(next_question.question_id)  # Track to avoid duplicates
        else:
            logger.info(f"[SESSION_END] Selected {len(selected_questions)}/{sample_size} questions (no more available)")
            break
    
    # Load Perseus items from MongoDB for all DASH-selected questions
    try:
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(selected_questions)
        logger.info(f"[MONGODB] Loaded {len(perseus_items)} Perseus questions from MongoDB with full metadata")
    except Exception as e:
        logger.error(f"[ERROR] MongoDB Perseus load failed: {e}. Local fallback disabled.")
        raise HTTPException(status_code=500, detail=f"Failed to load Perseus questions from MongoDB: {e}")
    
    if not perseus_items:
        logger.error(f"[ERROR] No Perseus questions found in MongoDB")
        raise HTTPException(status_code=404, detail="No Perseus questions found in MongoDB")
    
    logger.info(f"[SESSION_READY] Loaded {len(perseus_items)} Perseus questions (all with DASH intelligence)\n")
    
    # Return all questions (all selected by DASH with full intelligence)
    return perseus_items

@app.post("/api/question-displayed/{user_id}")
def log_question_displayed(user_id: str, display_info: dict):
    """Log when student views a question (Next button clicked)"""
    
    idx = display_info.get('question_index', 0)
    metadata = display_info.get('metadata', {})
    
    logger.info(f"\n{'='*80}")
    logger.info(f"[QUESTION_DISPLAYED] Question #{idx + 1}")
    logger.info(f"  Slug: {metadata.get('slug', 'unknown')}")
    logger.info(f"  DASH ID: {metadata.get('dash_question_id', 'unknown')}")
    logger.info(f"  Skills: {', '.join(metadata.get('skill_names', []))}")
    logger.info(f"  Difficulty: {metadata.get('difficulty', 0):.2f} | Expected: {metadata.get('expected_time_seconds', 0)}s")
    
    # Show current student state
    user_profile = dash_system.user_manager.load_user(user_id)
    if user_profile:
        current_time = time.time()
        scores = dash_system.get_skill_scores(user_id, current_time)
        
        # Only show practiced skills
        practiced = {k: v for k, v in scores.items() if v['practice_count'] > 0}
        
        if practiced:
            logger.info(f"\n[STUDENT_STATE]")
            logger.info(f"  {'Skill':<20} | {'Mem':<6} | {'Prob':<6} | {'Prac':<5} | {'Acc':<6}")
            logger.info(f"  {'-'*58}")
            for skill_id, data in list(practiced.items())[:5]:  # Show top 5
                logger.info(
                    f"  {data['name'][:20]:<20} | "
                    f"{data['memory_strength']:<6.2f} | "
                    f"{data['probability']:<6.2f} | "
                    f"{data['practice_count']:<5} | "
                    f"{data['accuracy']:<6.1%}"
                )
    
    logger.info(f"{'='*80}\n")
    return {"success": True}

@app.get("/next-question/{user_id}", response_model=Question)
def get_next_question(user_id: str):
    """
    Gets the next recommended question for a given user.
    (Original endpoint kept for backward compatibility)
    """
    # Ensure the user exists and is loaded
    dash_system.load_user_or_create(user_id)
    
    # Get the next question
    next_question = dash_system.get_next_question(user_id, time.time())
    
    if next_question:
        return next_question
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No recommended question found.")

class AnswerSubmission(BaseModel):
    question_id: str
    skill_ids: List[str]
    is_correct: bool
    response_time_seconds: float

@app.post("/api/submit-answer/{user_id}")
def submit_answer(user_id: str, answer: AnswerSubmission):
    """
    Record a question attempt and update DASH system.
    This enables tracking and adaptive difficulty.
    """
    logger.info(f"\n{'-'*80}")
    
    user_profile = dash_system.user_manager.load_user(user_id)
    if not user_profile:
        logger.error(f"[ERROR] User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Record the attempt using DASH system
    affected_skills = dash_system.record_question_attempt(
        user_profile, answer.question_id, answer.skill_ids, 
        answer.is_correct, answer.response_time_seconds
    )
    
    # Get updated scores for detailed logging
    user_profile_refreshed = dash_system.user_manager.load_user(user_id)
    current_time = time.time()
    new_scores = dash_system.get_skill_scores(user_id, current_time)
    
    # Log detailed skill changes
    if affected_skills:
        logger.info(f"\n  [SKILL_UPDATES]")
        for skill_id in affected_skills[:3]:  # Show top 3 to keep readable
            if skill_id in new_scores:
                data = new_scores[skill_id]
                skill_type = "DIRECT" if skill_id in answer.skill_ids else "PREREQ"
                logger.info(
                    f"    {data['name'][:20]:<20} ({skill_type:<6}): "
                    f"Mem {data['memory_strength']:.3f} | "
                    f"Prob {data['probability']:.3f}"
                )
    
    # Show performance summary after this question
    total_attempts = len(user_profile_refreshed.question_history)
    correct_count = sum(1 for attempt in user_profile_refreshed.question_history if attempt.is_correct)
    accuracy = (correct_count / total_attempts * 100) if total_attempts > 0 else 0
    
    logger.info(f"\n[PROGRESS] Total:{total_attempts} questions | Accuracy:{accuracy:.1f}% ({correct_count}/{total_attempts})")
    logger.info(f"{'-'*80}\n")
    
    return {
        "success": True,
        "affected_skills": affected_skills,
        "message": "Answer recorded successfully"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
