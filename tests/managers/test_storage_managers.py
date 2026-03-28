import enum
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from managers import mongodb_manager
from managers import user_manager


class FakeUsersCollection:
    def __init__(self, documents=None):
        self.documents = documents or {}
        self.inserted = []
        self.updated = []

    def find_one(self, query):
        if "user_id" in query:
            return self.documents.get(query["user_id"])
        if "google_id" in query:
            for document in self.documents.values():
                if document.get("google_id") == query["google_id"]:
                    return document
        return None

    def update_one(self, query, update, upsert=False):
        user_id = query["user_id"]
        current = self.documents.get(user_id, {"user_id": user_id})
        current.update(update["$set"])
        self.documents[user_id] = current
        self.updated.append((query, update, upsert))
        return SimpleNamespace(upserted_id=None)

    def insert_one(self, document):
        self.documents[document["user_id"]] = document
        self.inserted.append(document)
        return SimpleNamespace(inserted_id=document["user_id"])


class FakeMongoClient:
    def __init__(self, uri):
        self.uri = uri
        self.admin = SimpleNamespace(command=lambda name: {"ok": 1})
        self.closed = False
        self.databases = {
            "ai_tutor": {
                "users": "users-collection",
                "perseus_questions": "perseus-collection",
                "dash_questions": "dash-collection",
                "skills": "skills-collection",
                "generated_skills": "generated-skills",
                "scraped_questions": "scraped-questions",
                "sessions": "sessions-collection",
            }
        }

    def __getitem__(self, name):
        collections = self.databases[name]
        class FakeDB:
            def __init__(self, items):
                self.items = items

            def __getitem__(self, key):
                return self.items[key]

            def list_collection_names(self):
                return list(self.items.keys())

        return FakeDB(collections)

    def close(self):
        self.closed = True


def install_fake_dash_system(monkeypatch):
    fake_module = SimpleNamespace()

    class GradeLevel(enum.Enum):
        K = 0
        GRADE_1 = 1
        GRADE_7 = 7
        GRADE_12 = 12

    class DASHSystem:
        def __init__(self):
            self.skills = {
                "below": SimpleNamespace(grade_level=GradeLevel.GRADE_1),
                "at": SimpleNamespace(grade_level=GradeLevel.GRADE_7),
                "above": SimpleNamespace(grade_level=GradeLevel.GRADE_12),
            }

    fake_module.GradeLevel = GradeLevel
    fake_module.DASHSystem = DASHSystem
    monkeypatch.setitem(sys.modules, "services.DashSystem.dash_system", fake_module)
    return GradeLevel


def reset_mongo_singleton():
    mongodb_manager.MongoDBManager._instance = None
    mongodb_manager.MongoDBManager._client = None
    mongodb_manager.MongoDBManager._db = None


def test_mongodb_manager_connects_and_exposes_collections(monkeypatch):
    reset_mongo_singleton()
    monkeypatch.setenv("MONGODB_URI", "mongodb://example.test")
    monkeypatch.setattr(mongodb_manager, "MongoClient", FakeMongoClient)

    manager = mongodb_manager.MongoDBManager()
    assert manager.test_connection() is True
    assert manager.users == "users-collection"
    assert manager.sessions == "sessions-collection"

    manager.close()
    assert manager._client is None


def test_mongodb_manager_reports_connection_failure(monkeypatch):
    reset_mongo_singleton()
    monkeypatch.delenv("MONGODB_URI", raising=False)

    manager = mongodb_manager.MongoDBManager()
    assert manager.test_connection() is False


def test_user_manager_handles_grade_setup_storage_and_google_users(monkeypatch, tmp_path):
    install_fake_dash_system(monkeypatch)
    users_collection = FakeUsersCollection()
    fake_mongo = SimpleNamespace(users=users_collection)

    manager = user_manager.UserManager(use_mongodb=False)
    monkeypatch.setattr(manager, "mongo", fake_mongo)
    manager.use_mongodb = True

    assert user_manager.calculate_grade_from_age(5) == "K"
    assert user_manager.calculate_grade_from_age(18) == "GRADE_12"

    skills = manager.initialize_skills_for_grade(
        "GRADE_7",
        {
            "below": SimpleNamespace(grade_level=SimpleNamespace(value=1)),
            "at": SimpleNamespace(grade_level=SimpleNamespace(value=7)),
            "above": SimpleNamespace(grade_level=SimpleNamespace(value=12)),
        },
    )
    assert skills["below"].memory_strength == 2.0
    assert skills["at"].memory_strength == 0.0
    assert skills["above"].memory_strength == -2.0

    created = manager.create_new_user("user-1", all_skill_ids=["math"], age=9)
    assert created.current_grade == "GRADE_4"

    manager.add_question_attempt(created, "q1", ["math"], True, 2.5, time_penalty_applied=True)
    stats = manager.get_user_stats(created)
    assert stats["accuracy"] == 1.0
    assert stats["time_penalties"] == 1

    manager.users_folder = str(tmp_path)
    Path(tmp_path / "alpha.json").write_text("{}")
    assert manager.list_all_users() == ["alpha"]

    payload = created.to_dict()
    payload["_id"] = "mongo-id"
    payload["google_id"] = "google-1"
    users_collection.documents["user-1"] = payload
    loaded = manager.load_user("user-1")
    assert loaded.user_id == "user-1"
    assert manager.get_user_by_google_id("google-1").user_id == "user-1"

    existing = manager.get_or_create_user("user-1", all_skill_ids=["math", "science"])
    assert "science" in existing.skill_states

    google_user = manager.create_google_user(
        google_id="google-2",
        email="student@example.com",
        name="Student",
        age=12,
        picture="https://example.com/pic.png",
    )
    assert google_user.current_grade == "GRADE_7"
    assert users_collection.inserted[-1]["google_id"] == "google-2"

    manager.update_last_login("user-1")
    assert users_collection.updated


def test_user_manager_serialization_helpers():
    profile = user_manager.UserProfile(
        user_id="user-1",
        created_at=1.0,
        last_updated=2.0,
        skill_states={"math": user_manager.SkillState(0.5, None, 1, 1)},
        question_history=[user_manager.QuestionAttempt("q1", ["math"], True, 1.2, 3.0)],
        age=10,
        current_grade="GRADE_5",
    )
    profile.preloaded_question_ids = ["q1"]

    restored = user_manager.UserProfile.from_dict(profile.to_dict())
    assert restored.user_id == "user-1"
    assert restored.skill_states["math"].correct_count == 1
    assert restored.question_history[0].question_id == "q1"
