import sys
import types
import uuid
from enum import Enum
from types import SimpleNamespace

import pytest

import managers.mongodb_manager as mongodb_manager
import managers.user_manager as user_manager


class FakeUsersCollection:
    def __init__(self):
        self.docs = {}

    def _matches(self, doc, query):
        return all(doc.get(key) == value for key, value in query.items())

    def find_one(self, query):
        for doc in self.docs.values():
            if self._matches(doc, query):
                return dict(doc)
        return None

    def update_one(self, filter_doc, update_doc, upsert=False):
        existing = self.find_one(filter_doc) or {"user_id": filter_doc.get("user_id")}
        merged = {**existing, **update_doc["$set"]}
        self.docs[merged["user_id"]] = merged
        return SimpleNamespace(matched_count=1)

    def insert_one(self, doc):
        self.docs[doc["user_id"]] = dict(doc)
        return SimpleNamespace(inserted_id=doc["user_id"])


def install_fake_dash_system(monkeypatch):
    fake_module = types.ModuleType("services.DashSystem.dash_system")

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

    class Skill:
        def __init__(self, grade_level):
            self.grade_level = grade_level

    fake_skills = {
        "below": Skill(GradeLevel.GRADE_1),
        "at": Skill(GradeLevel.GRADE_4),
        "above": Skill(GradeLevel.GRADE_8),
    }

    class DASHSystem:
        def __init__(self):
            self.skills = fake_skills

    fake_module.GradeLevel = GradeLevel
    fake_module.DASHSystem = DASHSystem
    monkeypatch.setitem(sys.modules, "services.DashSystem.dash_system", fake_module)
    return fake_skills


def test_grade_and_profile_round_trip():
    assert user_manager.calculate_grade_from_age(5) == "K"
    assert user_manager.calculate_grade_from_age(9) == "GRADE_4"
    assert user_manager.calculate_grade_from_age(18) == "GRADE_12"

    skill_state = user_manager.SkillState(
        memory_strength=1.5,
        last_practice_time=123.0,
        practice_count=2,
        correct_count=1,
    )
    attempt = user_manager.QuestionAttempt(
        question_id="q-1",
        skill_ids=["s-1"],
        is_correct=True,
        response_time_seconds=2.5,
        timestamp=123.0,
        time_penalty_applied=False,
    )
    profile = user_manager.UserProfile(
        user_id="user-1",
        created_at=100.0,
        last_updated=100.0,
        skill_states={"s-1": skill_state},
        question_history=[attempt],
        age=9,
        current_grade="GRADE_4",
    )
    profile.preloaded_question_ids = ["q-1"]

    round_trip = user_manager.UserProfile.from_dict(profile.to_dict())
    assert round_trip.user_id == "user-1"
    assert round_trip.skill_states["s-1"].memory_strength == 1.5
    assert round_trip.question_history[0].question_id == "q-1"
    assert round_trip.preloaded_question_ids == ["q-1"]


def test_user_manager_create_load_and_stats(monkeypatch, tmp_path):
    fake_skills = install_fake_dash_system(monkeypatch)
    fake_mongo = SimpleNamespace(users=FakeUsersCollection())
    monkeypatch.setattr(mongodb_manager, "mongo_db", fake_mongo)
    monkeypatch.setattr(user_manager.time, "time", lambda: 100.0)

    manager = user_manager.UserManager(users_folder=str(tmp_path), use_mongodb=True)

    skill_states = manager.initialize_skills_for_grade("GRADE_4", fake_skills)
    assert skill_states["below"].memory_strength == 2.0
    assert skill_states["at"].memory_strength == 0.0
    assert skill_states["above"].memory_strength == -2.0

    profile = manager.create_new_user("user-1", all_skills=fake_skills, age=9)
    assert profile.current_grade == "GRADE_4"

    loaded = manager.load_user("user-1")
    assert loaded is not None
    assert loaded.user_id == "user-1"

    manager.add_question_attempt(loaded, "q-1", ["below"], is_correct=True, response_time_seconds=2.0)
    stats = manager.get_user_stats(loaded)
    assert stats == {
        "total_questions": 1,
        "correct_answers": 1,
        "accuracy": 1.0,
        "avg_response_time": 2.0,
        "time_penalties": 0,
        "skills_practiced": 0,
    }

    empty_profile = user_manager.UserProfile(
        user_id="empty",
        created_at=0.0,
        last_updated=0.0,
        skill_states={},
        question_history=[],
        age=7,
        current_grade="GRADE_2",
    )
    assert manager.get_user_stats(empty_profile)["accuracy"] == 0.0


def test_get_or_create_user_adds_missing_skills_and_file_helpers(monkeypatch, tmp_path):
    fake_mongo = SimpleNamespace(users=FakeUsersCollection())
    monkeypatch.setattr(mongodb_manager, "mongo_db", fake_mongo)
    manager = user_manager.UserManager(users_folder=str(tmp_path), use_mongodb=True)

    existing = user_manager.UserProfile(
        user_id="user-1",
        created_at=1.0,
        last_updated=1.0,
        skill_states={
            "existing": user_manager.SkillState(
                memory_strength=0.0,
                last_practice_time=None,
                practice_count=0,
                correct_count=0,
            )
        },
        question_history=[],
        age=7,
        current_grade="GRADE_2",
    )
    manager.save_user(existing)

    updated = manager.get_or_create_user("user-1", all_skill_ids=["existing", "new-skill"])
    assert "new-skill" in updated.skill_states

    manager.ensure_users_folder_exists()
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "b.json").write_text("{}")
    assert manager.get_user_file_path("a").endswith("a.json")
    assert sorted(manager.list_all_users()) == ["a", "b"]

    missing_mongo_manager = user_manager.UserManager(users_folder=str(tmp_path), use_mongodb=False)
    with pytest.raises(RuntimeError, match="MongoDB is required"):
        missing_mongo_manager.load_user("user-1")


def test_google_user_helpers(monkeypatch, tmp_path):
    install_fake_dash_system(monkeypatch)
    fake_mongo = SimpleNamespace(users=FakeUsersCollection())
    monkeypatch.setattr(mongodb_manager, "mongo_db", fake_mongo)
    monkeypatch.setattr(user_manager.time, "time", lambda: 200.0)
    monkeypatch.setattr(uuid, "uuid4", lambda: SimpleNamespace(hex="1234567890abcdef"))

    manager = user_manager.UserManager(users_folder=str(tmp_path), use_mongodb=True)
    created = manager.create_google_user(
        google_id="google-123",
        email="student@example.com",
        name="Student",
        age=10,
        picture="https://example.com/pic.png",
        user_type="student",
    )

    assert created.user_id == "user_1234567890ab"
    stored = fake_mongo.users.docs[created.user_id]
    assert stored["google_id"] == "google-123"
    assert stored["google_email"] == "student@example.com"

    loaded = manager.get_user_by_google_id("google-123")
    assert loaded is not None
    assert loaded.user_id == created.user_id

    manager.update_last_login(created.user_id)
    assert "last_login" in fake_mongo.users.docs[created.user_id]
    assert manager.get_user_by_google_id("missing") is None
