import math
import time
import json
import os
import sys
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from managers.user_manager import UserManager, UserProfile, SkillState

from shared.logging_config import get_logger

logger = get_logger(__name__)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Helper function for backward compatibility
def log_print(message: str):
    """Wrapper for logger.info for easier migration"""
    logger.info(message)

class GradeLevel(Enum):
    K = 0
    GRADE_1 = 1
    GRADE_2 = 2
    GRADE_3 = 3
    GRADE_4 = 4
    GRADE_5 = 5
    GRADE_6 = 6
    GRADE_7 = 7
    GRADE_8 = 8
    GRADE_9 = 9
    GRADE_10 = 10
    GRADE_11 = 11
    GRADE_12 = 12

@dataclass
class Skill:
    skill_id: str
    name: str
    grade_level: GradeLevel
    prerequisites: List[str] = field(default_factory=list)
    forgetting_rate: float = 0.1
    difficulty: float = 0.0
    order: int = 0  # Order within grade level for learning journey

@dataclass
class StudentSkillState:
    memory_strength: float = 0.0
    last_practice_time: Optional[float] = None
    practice_count: int = 0
    correct_count: int = 0

@dataclass
class Question:
    question_id: str
    skill_ids: List[str]
    content: str
    difficulty: float = 0.0
    expected_time_seconds: float = 60.0  # Default expected time for answering

class DASHSystem:
    def __init__(self, skills_file: Optional[str] = None, curriculum_file: Optional[str] = None, use_mongodb: bool = True):
        
        # Default file paths relative to the project root
        self.skills_file_path = skills_file if skills_file else "QuestionsBank/skills.json"
        self.curriculum_file_path = curriculum_file if curriculum_file else "QuestionsBank/curriculum.json"
        self.use_mongodb = use_mongodb

        self.skills: Dict[str, Skill] = {}
        self.student_states: Dict[str, Dict[str, StudentSkillState]] = {}
        # Lightweight index structures for efficient question loading
        self.question_index: Dict[str, str] = {}  # Maps question_id → skill_id (exerciseDirName)
        self.skill_question_index: Dict[str, List[str]] = {}  # Maps skill_id → [question_ids]
        self.question_cache: Dict[str, Question] = {}  # LRU cache for created Question objects
        self._cache_max_size = 10000  # LRU cache limit
        # Cache statistics for monitoring
        self._cache_hits = 0
        self._cache_misses = 0
        self.question_data_mode = "modern"
        # Keep questions dict for backward compatibility (will be populated on-demand)
        self.questions: Dict[str, Question] = {}  # Deprecated: use _get_or_create_question() instead
        self.curriculum: Dict = {}
        self.user_manager = UserManager(users_folder="Users")
        
        # Initialize MongoDB manager if using MongoDB
        self.mongo = None
        if use_mongodb:
            try:
                from managers.mongodb_manager import mongo_db
                self.mongo = mongo_db
                log_print("[MONGODB] MongoDB manager initialized")
            except Exception as e:
                log_print(f"[ERROR] Could not initialize MongoDB: {e}")
                raise RuntimeError(f"MongoDB initialization failed: {e}. Please configure MONGODB_URI in .env file.")
        
        # Load skills and questions from MongoDB only
        if self.use_mongodb and self.mongo:
            self._load_from_mongodb()
        else:
            raise RuntimeError("MongoDB is required. Please configure MONGODB_URI in .env file.")
    
    def _load_from_mongodb(self):
        """Load skills and questions from MongoDB"""
        try:
            modern_skill_count = self.mongo.generated_skills.count_documents({})
            modern_question_count = self.mongo.scraped_questions.count_documents({})
            legacy_skill_count = self.mongo.skills.count_documents({})
            legacy_question_count = self.mongo.dash_questions.count_documents({})

            if modern_skill_count > 0 and modern_question_count > 0:
                self.question_data_mode = "modern"
                log_print("[MONGODB] Using generated_skills + scraped_questions runtime data")
                self._load_skills_from_collection(list(self.mongo.generated_skills.find()))
                self._load_modern_question_index()
                return

            if legacy_skill_count > 0 and legacy_question_count > 0:
                self.question_data_mode = "legacy"
                log_print("[MONGODB] Falling back to legacy skills + dash_questions runtime data")
                if modern_skill_count > 0 and modern_question_count == 0:
                    log_print("[MONGODB] generated_skills is populated but scraped_questions is empty; using legacy compatibility mode")
                self._load_skills_from_collection(list(self.mongo.skills.find()))
                self._load_legacy_question_index()
                return

            raise RuntimeError(
                "No compatible MongoDB question dataset found. "
                "Expected either generated_skills + scraped_questions or skills + dash_questions."
            )
        except Exception as e:
            log_print(f"[ERROR] Error loading from MongoDB: {e}")
            raise RuntimeError(f"Failed to load data from MongoDB: {e}. Local fallback disabled.")

    def _load_skills_from_collection(self, skills_docs: List[Dict]):
        """Load skill definitions from a MongoDB collection."""
        self.skills.clear()

        for skill_doc in skills_docs:
            try:
                skill = Skill(
                    skill_id=skill_doc['skill_id'],
                    name=skill_doc['name'],
                    grade_level=GradeLevel[skill_doc['grade_level']],
                    prerequisites=skill_doc.get('prerequisites', []),
                    forgetting_rate=skill_doc.get('forgetting_rate', 0.1),
                    difficulty=skill_doc.get('difficulty', 0.0),
                    order=skill_doc.get('order', 0)
                )
                self.skills[skill.skill_id] = skill
            except KeyError as e:
                log_print(f"[WARNING] Skipping skill {skill_doc.get('skill_id', 'unknown')}: missing field {e}")

        log_print(f"[MONGODB] Loaded {len(self.skills)} skills from MongoDB")

    def _load_modern_question_index(self):
        """Build the runtime question index from scraped_questions."""
        valid_skill_ids = list(self.skills.keys())
        log_print(f"[MONGODB] Filtering questions by {len(valid_skill_ids)} valid skills at database level...")
        log_print("[MONGODB] Loading question index from scraped_questions collection (lightweight projection with skill filter)...")

        questions_cursor = self.mongo.scraped_questions.find(
            {"exerciseDirName": {"$in": valid_skill_ids}},
            {"questionId": 1, "exerciseDirName": 1}
        ).batch_size(1000)

        self.question_index.clear()
        self.skill_question_index.clear()

        question_count = 0
        processed_count = 0

        for q_doc in questions_cursor:
            question_count += 1
            if question_count % 1000 == 0:
                log_print(f"[MONGODB] Processed {question_count} questions so far...")

            try:
                question_id = q_doc.get('questionId', '')
                if not question_id:
                    continue

                exercise_dir_name = q_doc.get('exerciseDirName', '')
                if not exercise_dir_name:
                    log_print(f"[WARNING] Skipping question {question_id}: missing exerciseDirName")
                    continue

                if exercise_dir_name not in self.skills:
                    log_print(f"[WARNING] Question {question_id} has skill {exercise_dir_name} not in skills (unexpected after DB filter)")
                    continue

                self.question_index[question_id] = exercise_dir_name
                if exercise_dir_name not in self.skill_question_index:
                    self.skill_question_index[exercise_dir_name] = []
                self.skill_question_index[exercise_dir_name].append(question_id)
                processed_count += 1

            except KeyError as e:
                log_print(f"[WARNING] Skipping question {q_doc.get('questionId', 'unknown')}: missing field {e}")
            except Exception as e:
                log_print(f"[WARNING] Skipping question {q_doc.get('questionId', 'unknown')}: error {e}")

        log_print(f"[MONGODB] Loaded {len(self.question_index)} questions into index (processed {processed_count} out of {question_count} total documents)")
        log_print(f"[MONGODB] Index covers {len(self.skill_question_index)} skills")

    def _load_legacy_question_index(self):
        """Build the runtime question index from legacy dash_questions."""
        log_print("[MONGODB] Loading question index from legacy dash_questions collection...")

        self.question_index.clear()
        self.skill_question_index.clear()

        question_count = 0
        processed_count = 0

        for q_doc in self.mongo.dash_questions.find({}, {"question_id": 1, "skill_id": 1}):
            question_count += 1

            question_id = q_doc.get('question_id', '')
            skill_id = q_doc.get('skill_id', '')

            if not question_id or not skill_id:
                log_print(f"[WARNING] Skipping legacy question with missing identifiers: {q_doc}")
                continue

            if skill_id not in self.skills:
                log_print(f"[WARNING] Legacy question {question_id} has skill {skill_id} not present in skills collection")
                continue

            self.question_index[question_id] = skill_id
            if skill_id not in self.skill_question_index:
                self.skill_question_index[skill_id] = []
            self.skill_question_index[skill_id].append(question_id)
            processed_count += 1

        log_print(f"[MONGODB] Loaded {len(self.question_index)} legacy questions into index (processed {processed_count} out of {question_count} total documents)")
        log_print(f"[MONGODB] Legacy index covers {len(self.skill_question_index)} skills")
    
    def _get_or_create_question(self, question_id: str) -> Optional[Question]:
        """
        Get Question object from cache or create on-demand from index.
        This method implements lazy loading of Question objects for memory efficiency.
        
        Args:
            question_id: The question identifier
            
        Returns:
            Question object if found, None otherwise
        """
        # Check cache first (fast path)
        if question_id in self.question_cache:
            self._cache_hits += 1
            return self.question_cache[question_id]
        
        # Cache miss - will create new Question object
        self._cache_misses += 1
        
        # Check if question exists in index
        if question_id not in self.question_index:
            return None
        
        # Get skill_id from index
        skill_id = self.question_index[question_id]
        if skill_id not in self.skills:
            return None
        
        # Get difficulty from skill
        skill = self.skills[skill_id]
        difficulty = skill.difficulty
        
        # Create Question object on-demand
        question = Question(
            question_id=question_id,
            skill_ids=[skill_id],
            content="",  # Always empty, Perseus data loaded separately
            difficulty=difficulty,
            expected_time_seconds=60.0  # Default value
        )
        
        # Cache with LRU eviction (FIFO when cache is full)
        if len(self.question_cache) >= self._cache_max_size:
            # Remove oldest entry (FIFO eviction)
            oldest_key = next(iter(self.question_cache))
            del self.question_cache[oldest_key]
        
        self.question_cache[question_id] = question
        
        # Also update backward-compatible questions dict for existing code
        self.questions[question_id] = question
        
        # Log cache statistics periodically (every 100 misses)
        if self._cache_misses % 100 == 0:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
            log_print(f"[CACHE_STATS] Hits: {self._cache_hits}, Misses: {self._cache_misses}, Hit Rate: {hit_rate:.1f}%, Cache Size: {len(self.question_cache)}")
        
        return question
    
    def _load_from_files(self, skills_file: str, curriculum_file: str):
        """Load skills and curriculum from JSON files"""
        try:
            # Load skills
            with open(skills_file, 'r') as f:
                skills_data = json.load(f)
            
            # Track order within each grade level for learning journey
            grade_order_map = {}
            for skill_id, skill_data in skills_data.items():
                grade_level = GradeLevel[skill_data['grade_level']]
                # Use order from JSON if present, otherwise infer from position
                order = skill_data.get('order', 0)
                if order == 0:
                    # Infer order from position in file (for backward compatibility)
                    if grade_level not in grade_order_map:
                        grade_order_map[grade_level] = 0
                    grade_order_map[grade_level] += 1
                    order = grade_order_map[grade_level]
                
                skill = Skill(
                    skill_id=skill_data['skill_id'],
                    name=skill_data['name'],
                    grade_level=grade_level,
                    prerequisites=skill_data['prerequisites'],
                    forgetting_rate=skill_data['forgetting_rate'],
                    difficulty=skill_data['difficulty'],
                    order=order
                )
                self.skills[skill_id] = skill
            
            # Load curriculum and questions
            with open(curriculum_file, 'r') as f:
                self.curriculum = json.load(f)
            
            self.questions.clear()
            for grade_key, grade_data in self.curriculum['grades'].items():
                for skill_data in grade_data['skills']:
                    for question_data in skill_data['questions']:
                        question = Question(
                            question_id=question_data['question_id'],
                            skill_ids=[skill_data['skill_id']],
                            content=question_data['content'],
                            difficulty=question_data['difficulty'],
                            expected_time_seconds=question_data.get('expected_time_seconds', 60.0)
                        )
                        self.questions[question.question_id] = question
            
            log_print(f"[OK] Loaded {len(self.skills)} skills from JSON files")
            
        except FileNotFoundError as e:
            log_print(f"[ERROR] Error: Could not find file {e.filename}")
            log_print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
        except json.JSONDecodeError as e:
            log_print(f"[ERROR] Error: Invalid JSON format - {e}")
            log_print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
        except Exception as e:
            log_print(f"[ERROR] Unexpected error loading curriculum: {e}")
            log_print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
    
    def _initialize_k12_math_curriculum_fallback(self):
        """Fallback: Initialize K-12 Math curriculum with hardcoded skills (original implementation)"""
        
        # Kindergarten skills (order: 1, 2, 3)
        self.skills["counting_1_10"] = Skill("counting_1_10", "Counting 1-10", GradeLevel.K, [], 0.05, 0.0, 1)
        self.skills["number_recognition"] = Skill("number_recognition", "Number Recognition", GradeLevel.K, [], 0.05, 0.0, 2)
        self.skills["basic_shapes"] = Skill("basic_shapes", "Basic Shapes", GradeLevel.K, [], 0.08, 0.0, 3)
        
        # Grade 1 skills (order: 1, 2, 3)
        self.skills["addition_basic"] = Skill("addition_basic", "Basic Addition", GradeLevel.GRADE_1, ["counting_1_10"], 0.07, 0.0, 1)
        self.skills["subtraction_basic"] = Skill("subtraction_basic", "Basic Subtraction", GradeLevel.GRADE_1, ["counting_1_10"], 0.07, 0.0, 2)
        self.skills["counting_100"] = Skill("counting_100", "Counting to 100", GradeLevel.GRADE_1, ["counting_1_10"], 0.06, 0.0, 3)
        
        # Grade 2 skills (order: 1, 2, 3)
        self.skills["addition_2digit"] = Skill("addition_2digit", "2-Digit Addition", GradeLevel.GRADE_2, ["addition_basic"], 0.08, 0.0, 1)
        self.skills["subtraction_2digit"] = Skill("subtraction_2digit", "2-Digit Subtraction", GradeLevel.GRADE_2, ["subtraction_basic"], 0.08, 0.0, 2)
        self.skills["multiplication_intro"] = Skill("multiplication_intro", "Introduction to Multiplication", GradeLevel.GRADE_2, ["addition_basic"], 0.09, 0.0, 3)
        
        # Grade 3 skills (order: 1, 2, 3)
        self.skills["multiplication_tables"] = Skill("multiplication_tables", "Multiplication Tables", GradeLevel.GRADE_3, ["multiplication_intro"], 0.08, 0.0, 1)
        self.skills["division_basic"] = Skill("division_basic", "Basic Division", GradeLevel.GRADE_3, ["multiplication_tables"], 0.09, 0.0, 2)
        self.skills["fractions_intro"] = Skill("fractions_intro", "Introduction to Fractions", GradeLevel.GRADE_3, ["division_basic"], 0.10, 0.0, 3)
        
        # Grade 4 skills (order: 1, 2)
        self.skills["fractions_operations"] = Skill("fractions_operations", "Fraction Operations", GradeLevel.GRADE_4, ["fractions_intro"], 0.11, 0.0, 1)
        self.skills["decimals_intro"] = Skill("decimals_intro", "Introduction to Decimals", GradeLevel.GRADE_4, ["fractions_intro"], 0.10, 0.0, 2)
        
        # Grade 5 skills (order: 1, 2)
        self.skills["decimals_operations"] = Skill("decimals_operations", "Decimal Operations", GradeLevel.GRADE_5, ["decimals_intro"], 0.10, 0.0, 1)
        self.skills["percentages"] = Skill("percentages", "Percentages", GradeLevel.GRADE_5, ["decimals_operations"], 0.11, 0.0, 2)
        
        # Grade 6 skills (order: 1, 2)
        self.skills["integers"] = Skill("integers", "Integers", GradeLevel.GRADE_6, ["subtraction_2digit"], 0.09, 0.0, 1)
        self.skills["ratios_proportions"] = Skill("ratios_proportions", "Ratios and Proportions", GradeLevel.GRADE_6, ["fractions_operations"], 0.12, 0.0, 2)
        
        # Grade 7 skills (order: 1, 2)
        self.skills["algebraic_expressions"] = Skill("algebraic_expressions", "Algebraic Expressions", GradeLevel.GRADE_7, ["integers"], 0.13, 0.0, 1)
        self.skills["linear_equations_1var"] = Skill("linear_equations_1var", "Linear Equations (1 Variable)", GradeLevel.GRADE_7, ["algebraic_expressions"], 0.14, 0.0, 2)
        
        # Grade 8 skills (order: 1, 2)
        self.skills["linear_equations_2var"] = Skill("linear_equations_2var", "Linear Equations (2 Variables)", GradeLevel.GRADE_8, ["linear_equations_1var"], 0.15, 0.0, 1)
        self.skills["quadratic_intro"] = Skill("quadratic_intro", "Introduction to Quadratics", GradeLevel.GRADE_8, ["linear_equations_1var"], 0.16, 0.0, 2)
        
        # Grade 9 skills (Algebra 1) (order: 1, 2)
        self.skills["quadratic_equations"] = Skill("quadratic_equations", "Quadratic Equations", GradeLevel.GRADE_9, ["quadratic_intro"], 0.15, 0.0, 1)
        self.skills["polynomial_operations"] = Skill("polynomial_operations", "Polynomial Operations", GradeLevel.GRADE_9, ["algebraic_expressions"], 0.14, 0.0, 2)
        
        # Grade 10 skills (Geometry) (order: 1, 2)
        self.skills["geometric_proofs"] = Skill("geometric_proofs", "Geometric Proofs", GradeLevel.GRADE_10, ["basic_shapes"], 0.17, 0.0, 1)
        self.skills["trigonometry_basic"] = Skill("trigonometry_basic", "Basic Trigonometry", GradeLevel.GRADE_10, ["geometric_proofs"], 0.16, 0.0, 2)
        
        # Grade 11 skills (Algebra 2) (order: 1, 2)
        self.skills["exponentials_logs"] = Skill("exponentials_logs", "Exponentials and Logarithms", GradeLevel.GRADE_11, ["polynomial_operations"], 0.18, 0.0, 1)
        self.skills["trigonometry_advanced"] = Skill("trigonometry_advanced", "Advanced Trigonometry", GradeLevel.GRADE_11, ["trigonometry_basic"], 0.17, 0.0, 2)
        
        # Grade 12 skills (Pre-Calculus/Calculus) (order: 1, 2)
        self.skills["limits"] = Skill("limits", "Limits", GradeLevel.GRADE_12, ["exponentials_logs"], 0.19, 0.0, 1)
        self.skills["derivatives"] = Skill("derivatives", "Derivatives", GradeLevel.GRADE_12, ["limits"], 0.20, 0.0, 2)
    
    def get_student_state(self, student_id: str, skill_id: str) -> StudentSkillState:
        """Get or create student state for a specific skill"""
        if student_id not in self.student_states:
            self.student_states[student_id] = {}
        
        if skill_id not in self.student_states[student_id]:
            self.student_states[student_id][skill_id] = StudentSkillState()
        
        return self.student_states[student_id][skill_id]
    
    def calculate_memory_strength(self, student_id: str, skill_id: str, current_time: float) -> float:
        """Calculate current memory strength with decay.
        Mastered skills (probability >= 0.7) do not decay to preserve their score.
        """
        state = self.get_student_state(student_id, skill_id)
        skill = self.skills[skill_id]
        
        if state.last_practice_time is None:
            return state.memory_strength
        
        # Check if skill is mastered using stored strength (not decayed) to determine mastery
        # This prevents circular dependency: we need to check mastery before applying decay
        stored_strength = state.memory_strength
        logit = stored_strength - skill.difficulty
        probability = 1 / (1 + math.exp(-logit))
        
        # If skill is mastered (probability >= 0.7), return stored strength without decay
        # This preserves the score when moving to the next skill
        if probability >= 0.7:
            return stored_strength
        
        # Apply decay for non-mastered skills
        time_elapsed = current_time - state.last_practice_time
        decay_factor = math.exp(-skill.forgetting_rate * time_elapsed)
        
        return stored_strength * decay_factor
    
    def get_all_prerequisites(self, skill_id: str) -> List[str]:
        """Get all prerequisite skills recursively"""
        prerequisites = []
        skill = self.skills.get(skill_id)
        if not skill:
            return prerequisites
        
        for prereq_id in skill.prerequisites:
            prerequisites.append(prereq_id)
            # Recursively get prerequisites of prerequisites
            prerequisites.extend(self.get_all_prerequisites(prereq_id))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_prerequisites = []
        for prereq in prerequisites:
            if prereq not in seen:
                seen.add(prereq)
                unique_prerequisites.append(prereq)
        
        return unique_prerequisites
    
    def calculate_time_penalty(self, response_time_seconds: float) -> float:
        """Calculate time penalty multiplier for response time"""
        if response_time_seconds > 180:  # 3 minutes
            return 0.5
        return 1.0
    
    def predict_correctness(self, student_id: str, skill_id: str, current_time: float) -> float:
        """Predict probability of correct answer using sigmoid function"""
        memory_strength = self.calculate_memory_strength(student_id, skill_id, current_time)
        skill = self.skills[skill_id]
        
        # Sigmoid function: P(correct) = 1 / (1 + exp(-(memory_strength - difficulty)))
        logit = memory_strength - skill.difficulty
        return 1 / (1 + math.exp(-logit))
    
    def update_student_state(self, student_id: str, skill_id: str, is_correct: bool, current_time: float, response_time_seconds: float = 0.0):
        """Update student state after practice"""
        state = self.get_student_state(student_id, skill_id)
        skill = self.skills.get(skill_id)
        skill_name = skill.name if skill else skill_id
        
        # Store previous values for logging
        prev_strength = state.memory_strength
        prev_practice_count = state.practice_count
        prev_correct_count = state.correct_count
        
        # Update practice counts
        state.practice_count += 1
        if is_correct:
            state.correct_count += 1
        
        # Update memory strength based on performance
        # IMPORTANT: Use stored memory_strength (not decayed) as base for updates
        # Decay is only applied when calculating current strength for display/selection
        stored_strength = state.memory_strength
        time_since_last = current_time - state.last_practice_time if state.last_practice_time else 0
        
        # Update memory strength based on performance
        if is_correct:
            # Base strength increment with diminishing returns
            strength_increment = 1.0 / (1 + 0.1 * state.correct_count)
            
            # Apply time penalty using separate function
            time_penalty = self.calculate_time_penalty(response_time_seconds)
            strength_increment *= time_penalty
            
            # Update stored strength (absolute value, not decayed)
            new_strength = min(5.0, stored_strength + strength_increment)
            state.memory_strength = new_strength
            
            # Compact memory update log
            strength_change = new_strength - prev_strength
            log_print(f"  |- {skill_name}: {prev_strength:.3f} -> {new_strength:.3f} ({strength_change:+.3f})")
        else:
            # Slight decrease for incorrect answers
            # Use stored strength (not decayed) as base
            new_strength = max(-2.0, stored_strength - 0.2)
            state.memory_strength = new_strength
            
            # Compact memory update log
            strength_change = new_strength - prev_strength
            log_print(f"  |- {skill_name}: {prev_strength:.3f} -> {new_strength:.3f} ({strength_change:+.3f})")
        
        # Update last practice time
        state.last_practice_time = current_time
    
    def update_with_prerequisites(self, student_id: str, skill_ids: List[str], is_correct: bool, current_time: float, response_time_seconds: float = 0.0) -> List[str]:
        """Update student state including prerequisites on wrong answers"""
        all_affected_skills = []
        
        for skill_id in skill_ids:
            # Always update the direct skill
            self.update_student_state(student_id, skill_id, is_correct, current_time, response_time_seconds)
            all_affected_skills.append(skill_id)
            
            # If answer is wrong, also penalize prerequisites
            if not is_correct:
                prerequisites = self.get_all_prerequisites(skill_id)
                for prereq_id in prerequisites:
                    # Apply penalty to prerequisite (but don't count as practice attempt)
                    state = self.get_student_state(student_id, prereq_id)
                    current_strength = self.calculate_memory_strength(student_id, prereq_id, current_time)
                    
                    # Apply smaller penalty to prerequisites
                    state.memory_strength = max(-2.0, current_strength - 0.1)
                    state.last_practice_time = current_time
                    
                    all_affected_skills.append(prereq_id)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_affected_skills = []
        for skill_id in all_affected_skills:
            if skill_id not in seen:
                seen.add(skill_id)
                unique_affected_skills.append(skill_id)
        
        return unique_affected_skills
    
    def _initialize_unattempted_prerequisites(self, user_profile: UserProfile):
        """
        Initialize unattempted previous-grade skills to meet 0.7 threshold.
        For existing users: sets memory_strength=1.0 for all unattempted skills from grades below student's current grade.
        This ensures students can access grade-appropriate content without being blocked by empty skill history.
        """
        try:
            current_grade = GradeLevel[user_profile.current_grade]
        except KeyError:
            return  # Invalid grade, skip initialization
        
        current_grade_value = current_grade.value
        threshold = 0.7
        updated_count = 0
        
        # Find all skills from grades BELOW current grade (previous skills)
        for skill_id, skill in self.skills.items():
            # Only process skills from lower grades
            if skill.grade_level.value >= current_grade_value:
                continue
            
            # Ensure skill exists in skill_states (add if missing)
            if skill_id not in user_profile.skill_states:
                user_profile.skill_states[skill_id] = SkillState(
                    memory_strength=0.0,
                    last_practice_time=None,
                    practice_count=0,
                    correct_count=0
                )
            
            skill_state = user_profile.skill_states[skill_id]
            
            # Only update unattempted skills (practice_count == 0)
            if skill_state.practice_count > 0:
                continue
            
            # Calculate current probability: P(correct) = 1 / (1 + exp(-(memory_strength - difficulty)))
            logit = skill_state.memory_strength - skill.difficulty
            probability = 1 / (1 + math.exp(-logit))
            
            # If below threshold, set memory_strength to 1.0 (gives probability >= 0.7)
            if probability < threshold:
                skill_state.memory_strength = 1.0
                updated_count += 1
        
        if updated_count > 0:
            log_print(f"[PREV_SKILLS_INIT] Initialized {updated_count} unattempted previous-grade skills for grade {user_profile.current_grade}")
            # Save updated profile
            self.user_manager.save_user(user_profile)
    
    def load_user_or_create(self, user_id: str, age: int = 5) -> UserProfile:
        """Load existing user or create new one with cold-start initialization"""
        all_skill_ids = list(self.skills.keys())
        user_profile = self.user_manager.get_or_create_user(
            user_id, 
            all_skill_ids,
            all_skills=self.skills,  # Pass skills for cold-start
            age=age
        )
        
        # Initialize unattempted prerequisites (safe to run for all users - only updates if needed)
        self._initialize_unattempted_prerequisites(user_profile)
        
        # Sync user profile with current student_states for backward compatibility
        self.student_states[user_id] = {}
        for skill_id, skill_state in user_profile.skill_states.items():
            self.student_states[user_id][skill_id] = StudentSkillState(
                memory_strength=skill_state.memory_strength,
                last_practice_time=skill_state.last_practice_time,
                practice_count=skill_state.practice_count,
                correct_count=skill_state.correct_count
            )
        
        return user_profile
    
    def is_cold_start(self, user_profile: UserProfile) -> bool:
        """Check if user is in cold-start phase (first 20 questions)"""
        return len(user_profile.question_history) < 20
    
    def save_user_state(self, user_id: str, user_profile: UserProfile):
        """Save current student states back to user profile"""
        if user_id in self.student_states:
            for skill_id, student_state in self.student_states[user_id].items():
                if skill_id in user_profile.skill_states:
                    user_profile.skill_states[skill_id] = SkillState(
                        memory_strength=student_state.memory_strength,
                        last_practice_time=student_state.last_practice_time,
                        practice_count=student_state.practice_count,
                        correct_count=student_state.correct_count
                    )
        
        self.user_manager.save_user(user_profile)
    
    def record_question_attempt(self, user_profile: UserProfile, question_id: str, 
                              skill_ids: List[str], is_correct: bool, 
                              response_time_seconds: float):
        """Record a question attempt and update both memory and persistent storage"""
        current_time = time.time()
        time_penalty_applied = self.calculate_time_penalty(response_time_seconds) < 1.0
        
        # Get question details for logging (on-demand creation)
        question = self._get_or_create_question(question_id)
        question_difficulty = question.difficulty if question else "unknown"
        expected_time = question.expected_time_seconds if question else 0.0
        time_ratio = response_time_seconds / expected_time if expected_time > 0 else 0.0
        
        skill_names = [self.skills.get(sid).name if self.skills.get(sid) else sid for sid in skill_ids]
        
        result_str = 'CORRECT' if is_correct else 'INCORRECT'
        log_print(f"[ANSWER_SUBMITTED] Q:{question_id} | {result_str} | Time:{response_time_seconds:.1f}s | Skills:{','.join(skill_ids)}")
        
        # Update memory states
        affected_skills = self.update_with_prerequisites(
            user_profile.user_id, skill_ids, is_correct, current_time, response_time_seconds
        )
        
        # Save to persistent storage
        self.save_user_state(user_profile.user_id, user_profile)
        
        # Add to question history
        self.user_manager.add_question_attempt(
            user_profile, question_id, skill_ids, is_correct, 
            response_time_seconds, time_penalty_applied
        )
        
        return affected_skills
    
    def get_skill_scores(self, student_id: str, current_time: float) -> Dict[str, Dict[str, float]]:
        """Get all skill scores for a student"""
        scores = {}
        
        for skill_id, skill in self.skills.items():
            state = self.get_student_state(student_id, skill_id)
            memory_strength = self.calculate_memory_strength(student_id, skill_id, current_time)
            probability = self.predict_correctness(student_id, skill_id, current_time)
            
            scores[skill_id] = {
                'name': skill.name,
                'grade_level': skill.grade_level.name,
                'memory_strength': round(memory_strength, 3),
                'probability': round(probability, 3),
                'practice_count': state.practice_count,
                'correct_count': state.correct_count,
                'accuracy': round(state.correct_count / state.practice_count, 3) if state.practice_count > 0 else 0.0
            }
        
        return scores
    
    def get_recommended_skills(
        self, 
        student_id: str, 
        current_time: float, 
        threshold: float = 0.7,
        cold_start_grade_filter: Optional[str] = None,
        grade_range: int = 1
    ) -> List[str]:
        """
        Get skills that need practice based on memory strength decay.
        Returns skills sorted by learning journey: grade level -> order -> probability.
        
        Args:
            student_id: Unique student identifier
            current_time: Current timestamp
            threshold: Probability threshold for recommendations
            cold_start_grade_filter: If provided, only recommend skills within ±grade_range
            grade_range: How many grades above/below to include (default: 1)
        """
        recommendations = []
        skipped_prerequisites = []
        skipped_above_threshold = []
        skipped_grade_filter = []
        
        # Parse grade filter if provided
        target_grade = None
        if cold_start_grade_filter:
            try:
                target_grade = GradeLevel[cold_start_grade_filter]
            except KeyError:
                logger.warning(f"[FILTER] Invalid grade filter: {cold_start_grade_filter}")
        
        for skill_id, skill in self.skills.items():
            # Apply grade filter if in cold-start mode
            if target_grade is not None:
                grade_diff = abs(skill.grade_level.value - target_grade.value)
                if grade_diff > grade_range:
                    skipped_grade_filter.append((skill_id, skill.name, skill.grade_level.name))
                    continue
            
            probability = self.predict_correctness(student_id, skill_id, current_time)
            
            # Check if prerequisites are met
            prerequisites_met = True
            missing_prereqs = []
            for prereq_id in skill.prerequisites:
                prereq_prob = self.predict_correctness(student_id, prereq_id, current_time)
                if prereq_prob < threshold:
                    prerequisites_met = False
                    missing_prereqs.append((prereq_id, prereq_prob))
            
            # Recommend if probability is below threshold and prerequisites are met
            if probability < threshold and prerequisites_met:
                recommendations.append((skill_id, skill, probability))
            elif not prerequisites_met:
                skipped_prerequisites.append((skill_id, skill.name, missing_prereqs))
            elif probability >= threshold:
                skipped_above_threshold.append((skill_id, skill.name, probability))
        
        # Log grade filtering if applied
        if skipped_grade_filter and cold_start_grade_filter:
            log_print(f"[FILTER] Skipped {len(skipped_grade_filter)} skills outside grade range {cold_start_grade_filter}+-{grade_range}")
        
        # Log skill recommendation details for investigation
        if skipped_above_threshold:
            log_print(f"[SKILL_RECOMMEND] Skipped {len(skipped_above_threshold)} skills above threshold (>= {threshold}):")
            for skill_id, skill_name, prob in skipped_above_threshold[:5]:  # Show top 5
                log_print(f"  - {skill_name[:30]:<30} (prob: {prob:.3f})")
        
        if skipped_prerequisites:
            log_print(f"[SKILL_RECOMMEND] Skipped {len(skipped_prerequisites)} skills with unmet prerequisites")
        
        # Sort by learning journey: grade level (ascending) -> order (ascending) -> probability (ascending)
        # This ensures students follow a structured learning path
        recommendations.sort(key=lambda x: (
            x[1].grade_level.value,  # Grade level (K=0, Grade 1=1, etc.)
            x[1].order,                # Order within grade
            x[2]                       # Probability (lower = needs more practice)
        ))
        
        # Log recommended skills for investigation
        if recommendations:
            log_print(f"[SKILL_RECOMMEND] Found {len(recommendations)} skills needing practice (prob < {threshold}):")
            for skill_id, skill, prob in recommendations[:5]:  # Show top 5
                log_print(f"  - {skill.name[:30]:<30} (prob: {prob:.3f}, grade: {skill.grade_level.name}, order: {skill.order})")
        else:
            log_print(f"[SKILL_RECOMMEND] No skills found needing practice (all above threshold {threshold} or prerequisites unmet)")
        
        result = [skill_id for skill_id, _, _ in recommendations]
        return result
    
    def analyze_recent_performance(self, user_profile: UserProfile, lookback_count: int = 5) -> Dict[str, float]:
        """
        Analyze recent performance to determine difficulty adjustment.
        Returns a dict with:
        - 'performance_score': -1.0 (struggling) to 1.0 (excelling)
        - 'difficulty_adjustment': negative = easier, positive = harder
        - 'correctness_rate': 0.0 to 1.0
        - 'avg_time_ratio': average response time / expected time
        """
        if not user_profile.question_history or len(user_profile.question_history) == 0:
            # No history: start with medium difficulty
            log_print(f"[ADAPTIVE_DIFFICULTY] Student {user_profile.user_id}: No question history, using default difficulty (no adjustment)")
            return {
                'performance_score': 0.0,
                'difficulty_adjustment': 0.0,
                'correctness_rate': 0.5,
                'avg_time_ratio': 1.0
            }
        
        # Get recent attempts (last N questions)
        recent_attempts = user_profile.question_history[-lookback_count:]
        total_history = len(user_profile.question_history)
        
        # Calculate correctness rate
        correct_count = sum(1 for attempt in recent_attempts if attempt.is_correct)
        correctness_rate = correct_count / len(recent_attempts)
        
        # Calculate average response time ratio
        # Get expected time from questions (on-demand creation)
        time_ratios = []
        time_details = []
        for attempt in recent_attempts:
            question = self._get_or_create_question(attempt.question_id)
            if question and attempt.response_time_seconds > 0:
                expected_time = question.expected_time_seconds
                if expected_time > 0:
                    time_ratio = attempt.response_time_seconds / expected_time
                    time_ratios.append(time_ratio)
                    time_details.append((attempt.question_id, attempt.response_time_seconds, expected_time, time_ratio))
        
        avg_time_ratio = sum(time_ratios) / len(time_ratios) if time_ratios else 1.0
        
        # Calculate performance score
        # - Correctness contributes 60% weight
        # - Time efficiency contributes 40% weight
        correctness_score = (correctness_rate - 0.5) * 2.0  # -1.0 to 1.0
        time_score = (1.0 - min(avg_time_ratio, 2.0) / 2.0) * 2.0 - 1.0  # -1.0 to 1.0 (faster = better)
        
        performance_score = correctness_score * 0.6 + time_score * 0.4
        
        # Determine difficulty adjustment
        # If struggling (low correctness, slow): make easier (negative adjustment)
        # If excelling (high correctness, fast): make harder (positive adjustment)
        if performance_score < -0.3:
            # Struggling: easier questions (reduce difficulty by 0.2-0.4)
            difficulty_adjustment = -0.3
            performance_level = "STRUGGLING"
        elif performance_score < -0.1:
            # Slightly struggling: slightly easier (reduce by 0.1-0.2)
            difficulty_adjustment = -0.15
            performance_level = "SLIGHTLY_STRUGGLING"
        elif performance_score > 0.3:
            # Excelling: harder questions (increase difficulty by 0.2-0.4)
            difficulty_adjustment = 0.3
            performance_level = "EXCELLING"
        elif performance_score > 0.1:
            # Slightly excelling: slightly harder (increase by 0.1-0.2)
            difficulty_adjustment = 0.15
            performance_level = "SLIGHTLY_EXCELLING"
        else:
            # Balanced performance: maintain current difficulty
            difficulty_adjustment = 0.0
            performance_level = "BALANCED"
        
        # Removed verbose logging - only essential info logged elsewhere
        
        return {
            'performance_score': performance_score,
            'difficulty_adjustment': difficulty_adjustment,
            'correctness_rate': correctness_rate,
            'avg_time_ratio': avg_time_ratio
        }

    def get_next_question_flexible(self, student_id: str, current_time: float, exclude_question_ids: Optional[List[str]] = None, force_grade_range: bool = False, user_profile: Optional['UserProfile'] = None) -> Optional[Question]:
        """
        Flexible question selection that expands search when primary skills exhausted.
        Maintains full DASH intelligence (adaptive difficulty, learning journey).

        Args:
            student_id: Student identifier
            current_time: Current timestamp
            exclude_question_ids: Question IDs to exclude
            force_grade_range: If True, search all grade-appropriate skills (not just recommended)
            user_profile: Optional pre-loaded user profile to avoid redundant MongoDB calls

        Returns:
            Question with full DASH intelligence, or None if truly no questions available
        """
        # Load user profile once and reuse throughout
        if user_profile is None:
            user_profile = self.user_manager.load_user(student_id)
        if not user_profile:
            return None

        # First try normal DASH selection (recommended skills only)
        if not force_grade_range:
            question = self.get_next_question(student_id, current_time, is_retry=False, exclude_question_ids=exclude_question_ids, user_profile=user_profile)
            if question:
                return question
        
        # Get grade range (same as cold-start filtering)
        student_grade = GradeLevel[user_profile.current_grade]
        grade_min = max(0, student_grade.value - 1)
        grade_max = student_grade.value + 1
        
        # Get all skills in grade range, but exclude mastered skills (above threshold)
        # This ensures we don't fall back to skills that are already mastered
        current_time_for_check = time.time()
        threshold = 0.7  # Same threshold as get_recommended_skills
        grade_appropriate_skills = []
        for skill in self.skills.values():
            if grade_min <= skill.grade_level.value <= grade_max:
                # Check if skill is mastered (probability >= threshold)
                probability = self.predict_correctness(student_id, skill.skill_id, current_time_for_check)
                if probability < threshold:  # Only include skills that need practice
                    grade_appropriate_skills.append(skill)
                else:
                    log_print(f"[FLEXIBLE_SELECT] Skipping mastered skill: {skill.name} (prob: {probability:.3f} >= {threshold})")
        
        if not grade_appropriate_skills:
            log_print(f"[FLEXIBLE_SELECT] No grade-appropriate skills need practice (all mastered)")
            return None
        
        # Sort by learning journey (grade -> order -> current probability)
        skill_probabilities = []
        for skill in grade_appropriate_skills:
            prob = self.predict_correctness(student_id, skill.skill_id, current_time)
            skill_probabilities.append((skill.skill_id, skill, prob))
        
        # Sort by grade level, order, then probability (lower prob = needs more practice)
        skill_probabilities.sort(key=lambda x: (x[1].grade_level.value, x[1].order, x[2]))
        
        # Get answered questions to exclude
        answered_question_ids = {attempt.question_id for attempt in user_profile.question_history}
        if exclude_question_ids:
            answered_question_ids.update(exclude_question_ids)
        
        # Analyze performance for adaptive difficulty
        performance_analysis = self.analyze_recent_performance(user_profile)
        difficulty_adjustment = performance_analysis['difficulty_adjustment']
        
        # Try each skill in learning journey order with adaptive difficulty
        for skill_id, skill, probability in skill_probabilities:
            # Calculate target difficulty (same as normal DASH)
            base_difficulty = skill.difficulty
            target_difficulty = base_difficulty + difficulty_adjustment
            min_difficulty = max(0.0, target_difficulty - 0.2)
            max_difficulty = target_difficulty + 0.2
            
            # Get question IDs for this skill from index (fast lookup)
            skill_question_ids = self.skill_question_index.get(skill_id, [])
            if not skill_question_ids:
                continue
            
            # Filter out answered questions
            candidate_ids = [qid for qid in skill_question_ids if qid not in answered_question_ids]
            if not candidate_ids:
                continue
            
            # Create Question objects on-demand from index
            all_candidates = []
            for qid in candidate_ids:
                question = self._get_or_create_question(qid)
                if question:
                    all_candidates.append(question)
            
            if not all_candidates:
                continue
            
            # Filter by difficulty range (adaptive selection)
            filtered_candidates = [
                q for q in all_candidates
                if min_difficulty <= q.difficulty <= max_difficulty
            ]
            
            # Select best match
            if filtered_candidates:
                filtered_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
                selected = filtered_candidates[0]
                log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                          f"Difficulty:{selected.difficulty:.2f} (FLEXIBLE, target:{target_difficulty:.2f}, adj:{difficulty_adjustment:+.2f})")
                return selected
            
            # Use closest match if no exact difficulty match
            all_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
            selected = all_candidates[0]
            log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                      f"Difficulty:{selected.difficulty:.2f} (FLEXIBLE_FALLBACK, target:{target_difficulty:.2f})")
            return selected
        
        # Truly no questions available in grade range
        return None
    
    def get_next_question(self, student_id: str, current_time: float, is_retry: bool = False, exclude_question_ids: Optional[List[str]] = None, user_profile: Optional['UserProfile'] = None) -> Optional[Question]:
        """
        Get the next best question for the student, avoiding repeats.
        Intelligently selects question difficulty based on recent performance.
        If no questions are available, try to generate one.

        Args:
            user_profile: Optional pre-loaded user profile to avoid redundant MongoDB calls
        """
        # Use provided user_profile or load from DB (avoids redundant MongoDB calls)
        if user_profile is None:
            user_profile = self.user_manager.load_user(student_id)
        if not user_profile:
            return None
        
        # Apply grade filtering during cold-start phase (first 20 questions)
        # This ensures age-appropriate questions for new students
        cold_start_filter = None
        if self.is_cold_start(user_profile):
            cold_start_filter = user_profile.current_grade
        
        # Get recommended skills with optional grade filtering
        recommended_skills = self.get_recommended_skills(
            student_id, 
            current_time,
            cold_start_grade_filter=cold_start_filter,
            grade_range=1  # Allow ±1 grade level
        )
        
        if not recommended_skills:
            log_print(f"[GET_NEXT_QUESTION] No recommended skills found for student {student_id}")
            return None
        
        log_print(f"[GET_NEXT_QUESTION] Found {len(recommended_skills)} recommended skills for student {student_id}")
        
        answered_question_ids = {attempt.question_id for attempt in user_profile.question_history}
        
        # Also exclude questions that are already selected in the current batch
        if exclude_question_ids:
            answered_question_ids.update(exclude_question_ids)
        
        # Analyze recent performance to determine difficulty adjustment
        performance_analysis = self.analyze_recent_performance(user_profile)
        difficulty_adjustment = performance_analysis['difficulty_adjustment']
        
        # Try to find an unanswered question from the recommended skills with adaptive difficulty
        for skill_idx, skill_id in enumerate(recommended_skills, 1):
            skill = self.skills.get(skill_id)
            if not skill:
                continue
            
            # Calculate target difficulty range based on skill difficulty and performance
            base_difficulty = skill.difficulty
            target_difficulty = base_difficulty + difficulty_adjustment
            
            # Allow some flexibility: ±0.2 around target difficulty
            min_difficulty = max(0.0, target_difficulty - 0.2)
            max_difficulty = target_difficulty + 0.2
            
            # Reduced verbosity - only log when selecting a question
            
            # Get question IDs for this skill from index (fast lookup)
            skill_question_ids = self.skill_question_index.get(skill_id, [])
            if not skill_question_ids:
                continue  # Skip silently if no questions for this skill
            
            # Filter out answered questions
            candidate_ids = [qid for qid in skill_question_ids if qid not in answered_question_ids]
            if not candidate_ids:
                continue  # Skip silently if all questions already answered
            
            # Create Question objects on-demand from index
            all_candidates = []
            for qid in candidate_ids:
                question = self._get_or_create_question(qid)
                if question:
                    all_candidates.append(question)
            
            if not all_candidates:
                continue  # Skip silently
            
            # Filter by difficulty range (adaptive selection)
            filtered_candidates = [
                q for q in all_candidates
                if min_difficulty <= q.difficulty <= max_difficulty
            ]
            
            # If we have questions in the target difficulty range, use them
            if filtered_candidates:
                # Sort by how close they are to target difficulty, then return the best match
                filtered_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
                selected = filtered_candidates[0]
                log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                      f"Difficulty:{selected.difficulty:.2f} (target:{target_difficulty:.2f}, adj:{difficulty_adjustment:+.2f})")
                return selected
            
            # If no questions in target range, use closest match from all candidates
            # This ensures we always return a question if available
            all_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
            selected = all_candidates[0]
            log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                      f"Difficulty:{selected.difficulty:.2f} (FALLBACK, target:{target_difficulty:.2f})")
            return selected

        # No unanswered questions found
        return None
