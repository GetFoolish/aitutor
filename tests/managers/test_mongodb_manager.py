from types import SimpleNamespace

import pytest

import managers.mongodb_manager as mongodb_manager


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "users": SimpleNamespace(name="users"),
            "perseus_questions": SimpleNamespace(name="perseus_questions"),
            "dash_questions": SimpleNamespace(name="dash_questions"),
            "skills": SimpleNamespace(name="skills"),
            "generated_skills": SimpleNamespace(name="generated_skills"),
            "scraped_questions": SimpleNamespace(name="scraped_questions"),
            "sessions": SimpleNamespace(name="sessions"),
        }

    def __getitem__(self, key):
        return self.collections[key]

    def list_collection_names(self):
        return list(self.collections)


class FakeMongoClient:
    def __init__(self, uri):
        self.uri = uri
        self.admin = SimpleNamespace(command=lambda command: {"ok": 1})
        self.databases = {}
        self.closed = False

    def __getitem__(self, name):
        self.databases.setdefault(name, FakeDatabase())
        return self.databases[name]

    def close(self):
        self.closed = True


def reset_singleton():
    mongodb_manager.MongoDBManager._instance = None
    mongodb_manager.MongoDBManager._client = None
    mongodb_manager.MongoDBManager._db = None


def test_mongodb_manager_connects_and_exposes_collections(monkeypatch):
    reset_singleton()
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setenv("MONGODB_DB_NAME", "ai_tutor_test")
    monkeypatch.setattr(mongodb_manager, "MongoClient", FakeMongoClient)

    manager = mongodb_manager.MongoDBManager()

    assert manager.users.name == "users"
    assert manager.perseus_questions.name == "perseus_questions"
    assert manager.dash_questions.name == "dash_questions"
    assert manager.skills.name == "skills"
    assert manager.generated_skills.name == "generated_skills"
    assert manager.scraped_questions.name == "scraped_questions"
    assert manager.sessions.name == "sessions"
    assert manager.test_connection() is True

    manager.close()
    assert manager._client is None
    assert manager._db is None


def test_mongodb_manager_handles_missing_uri_and_connection_failure(monkeypatch):
    reset_singleton()
    monkeypatch.delenv("MONGODB_URI", raising=False)
    manager = mongodb_manager.MongoDBManager()

    with pytest.raises(ValueError, match="MONGODB_URI not found"):
        manager._connect()

    reset_singleton()
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setattr(mongodb_manager, "MongoClient", FakeMongoClient)
    manager = mongodb_manager.MongoDBManager()
    manager._ensure_connected()
    manager._client.admin = SimpleNamespace(command=lambda command: (_ for _ in ()).throw(RuntimeError("broken")))

    assert manager.test_connection() is False
