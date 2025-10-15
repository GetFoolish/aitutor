import math
import time
from typing import List, Optional
from pymongo.collection import Collection
from .db import get_collections
from .skills_cache import SKILLS_CACHE

class DASHSystem:
    """
    Main system for adaptive learning. Handles user progress tracking,
    skill recommendations, and question selection.
    """
    def __init__(self, users: Optional[Collection] = None, questions: Optional[Collection] = None):
        skills, questions_col, users_col = get_collections()
        self.skills: Collection = skills
        self.questions: Collection = questions or questions_col
        self.users: Collection = users or users_col

    def update_user_state_after_attempt(self, user_id: str, question_id: str, skill_ids: List[str], is_correct: bool, response_time_seconds: float) -> None:
        """Update user's skill states after they answer a question"""
        current_time = time.time()
        user_doc = self.users.find_one({"_id": user_id}) or {}

        if "skill_states" not in user_doc:
            user_doc["skill_states"] = {}

        update_operations = {}

        for skill_id in skill_ids:
            if skill_id not in SKILLS_CACHE:
                continue
            skill_info = SKILLS_CACHE[skill_id]
            state = user_doc["skill_states"].get(skill_id, {
                "memory_strength": 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0,
            })

            # Calculate how much they've forgotten since last practice
            time_elapsed = current_time - state["last_practice_time"] if state["last_practice_time"] else 0
            decay_factor = math.exp(-skill_info.get("forgetting_rate", 0.08) * time_elapsed)
            current_strength = state["memory_strength"] * decay_factor

            # Update strength based on whether they got it right
            if is_correct:
                # Diminishing returns - gets harder to improve as you get better
                strength_increment = 1.0 / (1 + 0.1 * state["correct_count"])
                new_strength = min(5.0, current_strength + strength_increment)
                state["correct_count"] += 1
            else:
                # Wrong answers reduce strength
                new_strength = max(-2.0, current_strength - 0.2)

            state["practice_count"] += 1

            update_operations[f"skill_states.{skill_id}.memory_strength"] = new_strength
            update_operations[f"skill_states.{skill_id}.last_practice_time"] = current_time
            update_operations[f"skill_states.{skill_id}.practice_count"] = state["practice_count"]
            update_operations[f"skill_states.{skill_id}.correct_count"] = state["correct_count"]

        attempt_log = {
            "question_id": question_id,
            "is_correct": is_correct,
            "timestamp": current_time,
            "response_time_seconds": response_time_seconds,
        }

        if update_operations:
            self.users.update_one(
                {"_id": user_id},
                {"$set": update_operations, "$push": {"question_history": attempt_log}},
                upsert=True,
            )

    def recommend_next_skills(self, user_id: str, mastery_threshold: float = 0.85) -> List[str]:
        """Figure out what skills the user should practice next"""
        doc = self.users.find_one({"_id": user_id}, {"skill_states": 1})
        if not doc or "skill_states" not in doc:
            # New user - start with the first skill
            if SKILLS_CACHE:
                return [next(iter(SKILLS_CACHE.keys()))]
            return []

        current_time = time.time()
        skill_probabilities = {}

        for skill_id, state in doc["skill_states"].items():
            if skill_id not in SKILLS_CACHE:
                continue
            skill_info = SKILLS_CACHE[skill_id]
            time_elapsed = current_time - state.get("last_practice_time") if state.get("last_practice_time") else 0
            decay_factor = math.exp(-skill_info.get("forgetting_rate", 0.08) * time_elapsed)
            current_strength = state.get("memory_strength", 0.0) * decay_factor
            logit = current_strength - skill_info.get("difficulty", 0.0)
            probability = 1 / (1 + math.exp(-logit))
            skill_probabilities[skill_id] = probability

        recommendations = []
        for skill_id, skill_info in SKILLS_CACHE.items():
            prob = skill_probabilities.get(skill_id, 0.0)
            if prob < mastery_threshold:
                prereqs_met = True
                for prereq_id in skill_info.get("prerequisites", []) or []:
                    if skill_probabilities.get(prereq_id, 0.0) < mastery_threshold:
                        prereqs_met = False
                        break
                if prereqs_met:
                    recommendations.append({"skill_id": skill_id, "probability": prob})

        recommendations.sort(key=lambda x: x["probability"])  # lowest first
        return [rec["skill_id"] for rec in recommendations]

    def select_next_question(self, user_id: str, recommended_skill_ids: List[str]) -> Optional[dict]:
        """Pick the next question for the user to practice"""
        if not recommended_skill_ids:
            return None
        doc = self.users.find_one({"_id": user_id}, {"question_history.question_id": 1})
        answered_ids = []
        if doc and "question_history" in doc:
            answered_ids = [item["question_id"] for item in doc["question_history"]]

        query = {"skill_ids": {"$in": recommended_skill_ids}, "_id": {"$nin": answered_ids}}
        return self.questions.find_one(query)
