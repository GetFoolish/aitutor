from pymongo import InsertOne
from src.dash_system.db import get_collections, ensure_indexes
from src.dash_system.skills_cache import init_skills_cache

SAMPLE_SKILLS = [
    {
        "_id": "introduction_to_multiplication",
        "name": "Intro to Multiplication",
        "learning_path": "3.2.0",
        "prerequisites": [],
        "difficulty": 0.1,
        "forgetting_rate": 0.08,
    },
    {
        "_id": "multiplication_single_digit",
        "name": "Single Digit Multiplication",
        "learning_path": "3.2.1",
        "prerequisites": ["introduction_to_multiplication"],
        "difficulty": 0.2,
        "forgetting_rate": 0.09,
    },
]


def main():
    ensure_indexes()
    skills, _, _ = get_collections()
    ops = [InsertOne(doc) for doc in SAMPLE_SKILLS]
    try:
        if ops:
            skills.bulk_write(ops, ordered=False)
    except Exception:
        # Ignore duplicate key errors on reseed
        pass
    count = init_skills_cache()
    print(f"Seeded skills. Cache size: {count}")


if __name__ == "__main__":
    main()
