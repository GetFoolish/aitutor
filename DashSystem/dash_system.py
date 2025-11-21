import math
import time
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from user_manager import UserManager, UserProfile, SkillState
from QuestionGeneratorAgent.question_generator_agent import QuestionGeneratorAgent

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

class DASHSystem:
    def __init__(self, skills_file: Optional[str] = None, curriculum_file: Optional[str] = None):
        
        # Default file paths relative to the project root
        self.skills_file_path = skills_file if skills_file else "QuestionsBank/skills.json"
        self.curriculum_file_path = curriculum_file if curriculum_file else "QuestionsBank/curriculum.json"

        self.skills: Dict[str, Skill] = {}
        self.student_states: Dict[str, Dict[str, StudentSkillState]] = {}
        self.questions: Dict[str, Question] = {}
        self.curriculum: Dict = {}
        self.user_manager = UserManager(users_folder="Users")
        
        # Initialize the Question Generator Agent
        try:
            # Get absolute path to curriculum file
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            qg_curriculum_path = os.path.join(project_root, "QuestionsBank", "curriculum.json")
            self.question_generator = QuestionGeneratorAgent(curriculum_file=qg_curriculum_path)
            print("Question Generator Agent initialized.")
        except Exception as e:
            self.question_generator = None
            print(f"Could not initialize Question Generator Agent: {e}")

        self._load_from_files(self.skills_file_path, self.curriculum_file_path)
    
    def _reload_questions(self):
        """Reload only the questions from the curriculum file."""
        try:
            with open(self.curriculum_file_path, 'r') as f:
                self.curriculum = json.load(f)
            
            self.questions.clear()
            for grade_key, grade_data in self.curriculum['grades'].items():
                for skill_data in grade_data['skills']:
                    for question_data in skill_data['questions']:
                        question = Question(
                            question_id=question_data['question_id'],
                            skill_ids=[skill_data['skill_id']],
                            content=question_data['content'],
                            difficulty=question_data['difficulty']
                        )
                        self.questions[question.question_id] = question
            print(f"[OK] Reloaded {len(self.questions)} questions from curriculum.")
        except Exception as e:
            print(f"[ERROR] Error reloading questions: {e}")

    def _load_from_files(self, skills_file: str, curriculum_file: str):
        """Load skills and curriculum from JSON files"""
        try:
            # Load skills
            with open(skills_file, 'r') as f:
                skills_data = json.load(f)
            
            for skill_id, skill_data in skills_data.items():
                grade_level = GradeLevel[skill_data['grade_level']]
                skill = Skill(
                    skill_id=skill_data['skill_id'],
                    name=skill_data['name'],
                    grade_level=grade_level,
                    prerequisites=skill_data['prerequisites'],
                    forgetting_rate=skill_data['forgetting_rate'],
                    difficulty=skill_data['difficulty']
                )
                self.skills[skill_id] = skill
            
            # Load curriculum and questions
            self._reload_questions()
            
            print(f"[OK] Loaded {len(self.skills)} skills from JSON files")
            
        except FileNotFoundError as e:
            print(f"[ERROR] Error: Could not find file {e.filename}")
            print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error: Invalid JSON format - {e}")
            print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
        except Exception as e:
            print(f"[ERROR] Unexpected error loading curriculum: {e}")
            print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
    
    def _initialize_k12_math_curriculum_fallback(self):
        """Fallback: Initialize K-12 Math curriculum with hardcoded skills (original implementation)"""
        
        # Kindergarten skills
        self.skills["counting_1_10"] = Skill("counting_1_10", "Counting 1-10", GradeLevel.K, [], 0.05)
        self.skills["number_recognition"] = Skill("number_recognition", "Number Recognition", GradeLevel.K, [], 0.05)
        self.skills["basic_shapes"] = Skill("basic_shapes", "Basic Shapes", GradeLevel.K, [], 0.08)
        
        # Grade 1 skills
        self.skills["addition_basic"] = Skill("addition_basic", "Basic Addition", GradeLevel.GRADE_1, ["counting_1_10"], 0.07)
        self.skills["subtraction_basic"] = Skill("subtraction_basic", "Basic Subtraction", GradeLevel.GRADE_1, ["counting_1_10"], 0.07)
        self.skills["counting_100"] = Skill("counting_100", "Counting to 100", GradeLevel.GRADE_1, ["counting_1_10"], 0.06)
        
        # Grade 2 skills
        self.skills["addition_2digit"] = Skill("addition_2digit", "2-Digit Addition", GradeLevel.GRADE_2, ["addition_basic"], 0.08)
        self.skills["subtraction_2digit"] = Skill("subtraction_2digit", "2-Digit Subtraction", GradeLevel.GRADE_2, ["subtraction_basic"], 0.08)
        self.skills["multiplication_intro"] = Skill("multiplication_intro", "Introduction to Multiplication", GradeLevel.GRADE_2, ["addition_basic"], 0.09)
        
        # Grade 3 skills
        self.skills["multiplication_tables"] = Skill("multiplication_tables", "Multiplication Tables", GradeLevel.GRADE_3, ["multiplication_intro"], 0.08)
        self.skills["division_basic"] = Skill("division_basic", "Basic Division", GradeLevel.GRADE_3, ["multiplication_tables"], 0.09)
        self.skills["fractions_intro"] = Skill("fractions_intro", "Introduction to Fractions", GradeLevel.GRADE_3, ["division_basic"], 0.10)
        
        # Grade 4 skills
        self.skills["fractions_operations"] = Skill("fractions_operations", "Fraction Operations", GradeLevel.GRADE_4, ["fractions_intro"], 0.11)
        self.skills["decimals_intro"] = Skill("decimals_intro", "Introduction to Decimals", GradeLevel.GRADE_4, ["fractions_intro"], 0.10)
        
        # Grade 5 skills
        self.skills["decimals_operations"] = Skill("decimals_operations", "Decimal Operations", GradeLevel.GRADE_5, ["decimals_intro"], 0.10)
        self.skills["percentages"] = Skill("percentages", "Percentages", GradeLevel.GRADE_5, ["decimals_operations"], 0.11)
        
        # Grade 6 skills
        self.skills["integers"] = Skill("integers", "Integers", GradeLevel.GRADE_6, ["subtraction_2digit"], 0.09)
        self.skills["ratios_proportions"] = Skill("ratios_proportions", "Ratios and Proportions", GradeLevel.GRADE_6, ["fractions_operations"], 0.12)
        
        # Grade 7 skills
        self.skills["algebraic_expressions"] = Skill("algebraic_expressions", "Algebraic Expressions", GradeLevel.GRADE_7, ["integers"], 0.13)
        self.skills["linear_equations_1var"] = Skill("linear_equations_1var", "Linear Equations (1 Variable)", GradeLevel.GRADE_7, ["algebraic_expressions"], 0.14)
        
        # Grade 8 skills
        self.skills["linear_equations_2var"] = Skill("linear_equations_2var", "Linear Equations (2 Variables)", GradeLevel.GRADE_8, ["linear_equations_1var"], 0.15)
        self.skills["quadratic_intro"] = Skill("quadratic_intro", "Introduction to Quadratics", GradeLevel.GRADE_8, ["linear_equations_1var"], 0.16)
        
        # Grade 9 skills (Algebra 1)
        self.skills["quadratic_equations"] = Skill("quadratic_equations", "Quadratic Equations", GradeLevel.GRADE_9, ["quadratic_intro"], 0.15)
        self.skills["polynomial_operations"] = Skill("polynomial_operations", "Polynomial Operations", GradeLevel.GRADE_9, ["algebraic_expressions"], 0.14)
        
        # Grade 10 skills (Geometry)
        self.skills["geometric_proofs"] = Skill("geometric_proofs", "Geometric Proofs", GradeLevel.GRADE_10, ["basic_shapes"], 0.17)
        self.skills["trigonometry_basic"] = Skill("trigonometry_basic", "Basic Trigonometry", GradeLevel.GRADE_10, ["geometric_proofs"], 0.16)
        
        # Grade 11 skills (Algebra 2)
        self.skills["exponentials_logs"] = Skill("exponentials_logs", "Exponentials and Logarithms", GradeLevel.GRADE_11, ["polynomial_operations"], 0.18)
        self.skills["trigonometry_advanced"] = Skill("trigonometry_advanced", "Advanced Trigonometry", GradeLevel.GRADE_11, ["trigonometry_basic"], 0.17)
        
        # Grade 12 skills (Pre-Calculus/Calculus)
        self.skills["limits"] = Skill("limits", "Limits", GradeLevel.GRADE_12, ["exponentials_logs"], 0.19)
        self.skills["derivatives"] = Skill("derivatives", "Derivatives", GradeLevel.GRADE_12, ["limits"], 0.20)
    
    def get_student_state(self, student_id: str, skill_id: str) -> StudentSkillState:
        """Get or create student state for a specific skill"""
        if student_id not in self.student_states:
            self.student_states[student_id] = {}
        
        if skill_id not in self.student_states[student_id]:
            self.student_states[student_id][skill_id] = StudentSkillState()
        
        return self.student_states[student_id][skill_id]
    
    def calculate_memory_strength(self, student_id: str, skill_id: str, current_time: float) -> float:
        """Calculate current memory strength with decay"""
        state = self.get_student_state(student_id, skill_id)
        skill = self.skills[skill_id]
        
        if state.last_practice_time is None:
            return state.memory_strength
        
        time_elapsed = current_time - state.last_practice_time
        decay_factor = math.exp(-skill.forgetting_rate * time_elapsed)
        
        return state.memory_strength * decay_factor
    
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
        
        # Update practice counts
        state.practice_count += 1
        if is_correct:
            state.correct_count += 1
        
        # Calculate current memory strength with decay
        current_strength = self.calculate_memory_strength(student_id, skill_id, current_time)
        
        # Update memory strength based on performance
        if is_correct:
            # Base strength increment with diminishing returns
            strength_increment = 1.0 / (1 + 0.1 * state.correct_count)
            
            # Apply time penalty using separate function
            time_penalty = self.calculate_time_penalty(response_time_seconds)
            strength_increment *= time_penalty
            
            state.memory_strength = min(5.0, current_strength + strength_increment)
        else:
            # Slight decrease for incorrect answers
            state.memory_strength = max(-2.0, current_strength - 0.2)
        
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
    
    def load_user_or_create(self, user_id: str) -> UserProfile:
        """Load existing user or create new one with all skills initialized"""
        all_skill_ids = list(self.skills.keys())
        user_profile = self.user_manager.get_or_create_user(user_id, all_skill_ids)
        
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
    
    def get_recommended_skills(self, student_id: str, current_time: float, threshold: float = 0.7) -> List[str]:
        """Get skills that need practice based on memory strength decay"""
        recommendations = []
        
        for skill_id, skill in self.skills.items():
            probability = self.predict_correctness(student_id, skill_id, current_time)
            
            # Check if prerequisites are met
            prerequisites_met = True
            for prereq_id in skill.prerequisites:
                prereq_prob = self.predict_correctness(student_id, prereq_id, current_time)
                if prereq_prob < threshold:
                    prerequisites_met = False
                    break
            
            # Recommend if probability is below threshold and prerequisites are met
            if probability < threshold and prerequisites_met:
                recommendations.append(skill_id)
        
        return recommendations

    def get_next_question(self, student_id: str, current_time: float, is_retry: bool = False) -> Optional[Question]:
        """
        Get the next best question for the student, avoiding repeats.
        If no questions are available, try to generate one.
        """
        recommended_skills = self.get_recommended_skills(student_id, current_time)
        
        if not recommended_skills:
            return None

        user_profile = self.user_manager.load_user(student_id)
        if not user_profile:
            return None
        
        answered_question_ids = {attempt.question_id for attempt in user_profile.question_history}
        
        # Try to find an unanswered question from the recommended skills
        for skill_id in recommended_skills:
            candidate_questions = [
                q for q in self.questions.values() 
                if skill_id in q.skill_ids and q.question_id not in answered_question_ids
            ]
            
            if candidate_questions:
                return candidate_questions[0]

        # If we're here, no unanswered questions were found. Time to generate one.
        if is_retry or self.question_generator is None:
            print("No unanswered questions found and cannot generate new ones.")
            return None

        print("[INFO] No unanswered questions available. Attempting to generate a new one...")
        
        top_skill_id = recommended_skills[0]
        
        source_question_id = None
        # Find the most recently answered question for this skill to use as a template
        for attempt in reversed(user_profile.question_history):
            if top_skill_id in attempt.skill_ids:
                source_question_id = attempt.question_id
                break
        
        if not source_question_id:
            # Fallback: find any question for the skill
            all_skill_questions = [q.question_id for q in self.questions.values() if top_skill_id in q.skill_ids]
            if all_skill_questions:
                source_question_id = all_skill_questions[0]

        if not source_question_id:
            print(f"Could not find any source question for skill {top_skill_id} to generate a variation.")
            return None

        try:
            print(f"[INFO] Generating variation based on question {source_question_id} for skill {top_skill_id}...")
            generated_ids = self.question_generator.generate_variations(source_question_id, num_variations=1)
            
            if generated_ids:
                print(f"[OK] Successfully generated {len(generated_ids)} new question(s).")
                self._reload_questions()
                # Retry finding a question
                return self.get_next_question(student_id, current_time, is_retry=True)
            else:
                print("[WARNING] Question generation did not produce any new questions.")
                return None
        except Exception as e:
            print(f"[ERROR] Error during question generation: {e}")
            return None