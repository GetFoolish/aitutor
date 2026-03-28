import json
import sys
import types
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

import pytest

import managers.config_manager as config_manager
import managers.mongodb_manager as mongodb_manager
import managers.user_manager as user_manager


class FakeUsersCollection:
    def __init__(self):
        self.docs = {}

    def _find(self, query):
        for doc in self.docs.values():
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None

    def find_one(self, query):
        doc = self._find(query)
        return None if doc is None else dict(doc)

    def update_one(self, query, update, upsert=False):
        doc = self._find(query)
        if doc is None and upsert:
            doc = dict(query)
            self.docs[query["user_id"]] = doc
        if doc is not None:
            doc.update(update.get("$set", {}))
        return SimpleNamespace(modified_count=1 if doc is not None else 0)

    def insert_one(self, document):
        self.docs[document["user_id"]] = dict(document)
        return SimpleNamespace(inserted_id=document["user_id"])


class FakeMongo:
    def __init__(self):
        self.users = FakeUsersCollection()


class FakeMongoDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        self.collections.setdefault(name, [])
        return self.collections[name]

    def list_collection_names(self):
        return list(self.collections)


class FakeMongoClient:
    def __init__(self, uri):
        self.uri = uri
        self.db = FakeMongoDatabase()
        self.admin = SimpleNamespace(command=lambda command: {"ok": 1} if command == "ping" else None)
        self.closed = False

    def __getitem__(self, name):
        return self.db

    def close(self):
        self.closed = True


def install_fake_dash_module(monkeypatch):
    grade_level = Enum(
        "GradeLevel",
        {"K": 0, "GRADE_1": 1, "GRADE_2": 2, "GRADE_7": 7, "GRADE_12": 12},
    )
    fake_skills = {
        "skill-k": SimpleNamespace(grade_level=grade_level.K),
        "skill-2": SimpleNamespace(grade_level=grade_level.GRADE_2),
        "skill-7": SimpleNamespace(grade_level=grade_level.GRADE_7),
    }

    fake_dash_module = types.ModuleType("services.DashSystem.dash_system")
    fake_dash_module.GradeLevel = grade_level
    fake_dash_module.DASHSystem = lambda: SimpleNamespace(skills=fake_skills)
    monkeypatch.setitem(sys.modules, "services.DashSystem.dash_system", fake_dash_module)
    return fake_skills


def build_user_manager(monkeypatch):
    fake_mongo = FakeMongo()
    manager = user_manager.UserManager(use_mongodb=False)
    manager.use_mongodb = True
    manager.mongo = fake_mongo
    monkeypatch.setattr(user_manager.time, "time", lambda: 100.0)
    return manager, fake_mongo


def test_config_manager_reads_env_and_updates_models(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "llm_models": {"grading": {"model": "initial-model"}},
                "api_endpoints": {"openrouter": "https://openrouter.ai/api/v1"},
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

    manager = config_manager.ConfigManager(config_path="config.json")
    assert manager.get_api_key("openrouter") == "openrouter-key"
    assert manager.get_api_key("google") == "google-key"
    assert manager.get_llm_config("grading") == {"model": "initial-model"}
    assert manager.get_api_endpoint("openrouter") == "https://openrouter.ai/api/v1"

    manager.update_model("grading", "updated-model")
    assert json.loads(config_path.read_text())["llm_models"]["grading"]["model"] == "updated-model"

    with pytest.raises(ValueError):
        manager.get_api_key("unknown")
    with pytest.raises(ValueError):
        manager.get_llm_config("missing")
    with pytest.raises(ValueError):
        manager.get_api_endpoint("missing")


def test_mongodb_manager_connects_tests_and_closes(monkeypatch):
    mongodb_manager.MongoDBManager._instance = None
    mongodb_manager.MongoDBManager._client = None
    mongodb_manager.MongoDBManager._db = None

    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setenv("MONGODB_DB_NAME", "ai_tutor")
    monkeypatch.setattr(mongodb_manager, "MongoClient", FakeMongoClient)

    manager = mongodb_manager.MongoDBManager()

    assert manager.db is manager._db
    assert manager.users == []
    assert manager.perseus_questions == []
    assert manager.dash_questions == []
    assert manager.skills == []
    assert manager.generated_skills == []
    assert manager.scraped_questions == []
    assert manager.sessions == []
    assert manager.test_connection() is True

    manager.close()
    assert manager._client is None
    assert manager._db is None


def test_mongodb_manager_requires_uri(monkeypatch):
    mongodb_manager.MongoDBManager._instance = None
    mongodb_manager.MongoDBManager._client = None
    mongodb_manager.MongoDBManager._db = None

    monkeypatch.delenv("MONGODB_URI", raising=False)
    manager = mongodb_manager.MongoDBManager()

    with pytest.raises(ValueError):
        manager._connect()


def test_user_manager_creates_loads_and_updates_profiles(monkeypatch, tmp_path):
    fake_skills = install_fake_dash_module(monkeypatch)
    manager, fake_mongo = build_user_manager(monkeypatch)

    profile = manager.create_new_user("user-123", all_skills=fake_skills, age=7)
    assert profile.current_grade == "GRADE_2"
    assert set(profile.skill_states) == {"skill-k", "skill-2", "skill-7"}
    assert fake_mongo.users.docs["user-123"]["current_grade"] == "GRADE_2"

    loaded = manager.load_user("user-123")
    assert loaded.user_id == "user-123"
    assert loaded.current_grade == "GRADE_2"

    manager.add_question_attempt(
        loaded,
        question_id="q-1",
        skill_ids=["skill-2"],
        is_correct=True,
        response_time_seconds=4.5,
        time_penalty_applied=True,
    )
    stats = manager.get_user_stats(loaded)
    assert stats["total_questions"] == 1
    assert stats["correct_answers"] == 1
    assert stats["time_penalties"] == 1

    existing = manager.get_or_create_user("user-123", all_skill_ids=["skill-2", "skill-new"])
    assert "skill-new" in existing.skill_states

    created = manager.get_or_create_user("user-999", all_skill_ids=["skill-a"], age=10)
    assert created.user_id == "user-999"
    assert created.current_grade == "GRADE_5"

    assert manager.get_user_file_path("user-123").endswith("Users/user-123.json")
    assert manager.user_exists("missing") is False


def test_user_manager_google_helpers_and_folder_listing(monkeypatch, tmp_path):
    install_fake_dash_module(monkeypatch)
    manager, fake_mongo = build_user_manager(monkeypatch)
    manager.users_folder = str(tmp_path)

    profile = manager.create_google_user(
        google_id="google-123",
        email="student@example.com",
        name="Student",
        age=12,
        picture="https://example.com/p.png",
        user_type="student",
    )

    stored = fake_mongo.users.docs[profile.user_id]
    assert stored["google_id"] == "google-123"
    assert stored["google_email"] == "student@example.com"
    assert stored["current_grade"] == "GRADE_7"

    looked_up = manager.get_user_by_google_id("google-123")
    assert looked_up.user_id == profile.user_id

    manager.update_last_login(profile.user_id)
    assert "last_login" in fake_mongo.users.docs[profile.user_id]

    (tmp_path / "first.json").write_text("{}")
    (tmp_path / "second.json").write_text("{}")
    assert sorted(manager.list_all_users()) == ["first", "second"]


def test_user_manager_supports_error_paths(monkeypatch):
    install_fake_dash_module(monkeypatch)
    manager = user_manager.UserManager(use_mongodb=False)
    manager.use_mongodb = False
    manager.mongo = None

    assert user_manager.calculate_grade_from_age(5) == "K"
    assert user_manager.calculate_grade_from_age(18) == "GRADE_12"
    assert user_manager.calculate_grade_from_age(9) == "GRADE_4"

    skill_state = user_manager.SkillState(1.0, 123.0, 4, 3)
    round_trip = user_manager.SkillState.from_dict(skill_state.to_dict())
    assert round_trip == skill_state

    profile = user_manager.UserProfile(
        user_id="user-1",
        created_at=1.0,
        last_updated=2.0,
        skill_states={},
        question_history=[],
        age=6,
        current_grade="GRADE_1",
    )
    profile.preloaded_question_ids = ["q-1"]
    restored = user_manager.UserProfile.from_dict(profile.to_dict())
    assert restored.preloaded_question_ids == ["q-1"]

    with pytest.raises(RuntimeError):
        manager.load_user("missing")
    with pytest.raises(RuntimeError):
        manager.save_user(profile)
