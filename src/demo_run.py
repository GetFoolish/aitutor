from src.dash_system.db import ensure_indexes
from src.dash_system.skills_cache import init_skills_cache
from src.dash_system.dash import DASHSystem


def main():
    ensure_indexes()
    init_skills_cache()

    dash = DASHSystem()
    user_id = "student007"

    # Initial recommendation
    skills = dash.recommend_next_skills(user_id)
    print("Recommended skills:", skills)

    # Pick question
    q = dash.select_next_question(user_id, skills)
    print("Next question:", q and q.get("_id"))

    # Simulate a correct attempt
    if q:
        dash.update_user_state_after_attempt(user_id, q["_id"], q.get("skill_ids", []), True, 2.5)
        print("Logged attempt.")

    # Re-recommend
    skills2 = dash.recommend_next_skills(user_id)
    print("Recommended skills after attempt:", skills2)


if __name__ == "__main__":
    main()
