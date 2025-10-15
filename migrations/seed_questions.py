from pymongo import InsertOne
from src.dash_system.db import get_collections, ensure_indexes

SAMPLE_QUESTIONS = [
    {
        "_id": "q_mult_3x4",
        "skill_ids": ["multiplication_single_digit"],
        "learning_path": "3.2.1.1",
        "difficulty_level": 0.2,
        "question_type": "numeric-input",
        "tags": ["arithmetic", "mental-math"],
        "content": "What is 3 × 4?",
    },
    {
        "_id": "q_mult_8x7",
        "skill_ids": ["multiplication_single_digit"],
        "learning_path": "3.2.1.4",
        "difficulty_level": 0.25,
        "question_type": "numeric-input",
        "tags": ["arithmetic", "mental-math"],
        "content": "What is 8 × 7?",
    },
    {
        "_id": "q_mult_5x9",
        "skill_ids": ["multiplication_single_digit"],
        "learning_path": "3.2.1.5",
        "difficulty_level": 0.25,
        "question_type": "numeric-input",
        "tags": ["arithmetic", "single-digit"],
        "content": "What is 5 × 9?",
    },
]


def main():
    ensure_indexes()
    _, questions, _ = get_collections()
    ops = [InsertOne(doc) for doc in SAMPLE_QUESTIONS]
    try:
        if ops:
            questions.bulk_write(ops, ordered=False)
    except Exception:
        # Ignore duplicate key errors on reseed
        pass
    print("Seeded sample questions.")


if __name__ == "__main__":
    main()
