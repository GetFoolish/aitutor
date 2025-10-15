import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true", reason="Skip DB tests on CI unless Mongo is available"
)


def test_dash_flow():
    from src.dash_system.db import ensure_indexes
    from src.dash_system.skills_cache import init_skills_cache
    from src.dash_system.dash import DASHSystem
    from migrations.seed_skills import main as seed_main

    ensure_indexes()
    seed_main()
    init_skills_cache()

    dash = DASHSystem()
    user_id = "student007"

    dash.update_user_state_after_attempt(user_id, "q1", ["multiplication_single_digit"], True, 2.0)
    skills = dash.recommend_next_skills(user_id)

    assert isinstance(skills, list)
