from typing import List, Dict
from pymongo import InsertOne
from src.dash_system.db import get_collections


def transform_user(raw: Dict) -> Dict:
    return {
        "_id": raw["_id"],
        "skill_states": raw.get("skill_states", {}),
        "question_history": raw.get("question_history", []),
    }


def migrate_users(raw_users: List[Dict]) -> int:
    _, _, users = get_collections()
    ops = [InsertOne(transform_user(u)) for u in raw_users]
    if not ops:
        return 0
    try:
        users.bulk_write(ops, ordered=False)
    except Exception:
        pass
    return len(ops)


if __name__ == "__main__":
    print("Provide raw users list to migrate_users([...])")
