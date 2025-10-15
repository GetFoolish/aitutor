from typing import List, Dict
from pymongo import InsertOne
from src.dash_system.db import get_collections


def transform_question(raw: Dict) -> Dict:
    return {
        "_id": raw["_id"],
        "skill_ids": raw.get("skill_ids", []),
        "learning_path": raw.get("learning_path"),
        "difficulty_level": raw.get("difficulty_level", 0.0),
        "question_type": raw.get("question_type"),
        "tags": raw.get("tags", []),
        "content": raw.get("content"),
    }


def migrate_questions(raw_questions: List[Dict]) -> int:
    _, questions, _ = get_collections()
    ops = [InsertOne(transform_question(q)) for q in raw_questions]
    if not ops:
        return 0
    try:
        questions.bulk_write(ops, ordered=False)
    except Exception:
        pass
    return len(ops)


if __name__ == "__main__":
    # Example usage placeholder
    print("Provide raw questions list to migrate_questions([...])")
