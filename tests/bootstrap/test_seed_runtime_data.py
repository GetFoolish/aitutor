from types import SimpleNamespace

import scripts.seed_runtime_data as seed_runtime_data


class FakeCollection:
    def __init__(self, state: dict[str, int], name: str):
        self._state = state
        self._name = name

    def count_documents(self, _query):
        return self._state.get(self._name, 0)


class FakeDatabase:
    def __init__(self, state: dict[str, int]):
        self._state = state

    def __getitem__(self, name: str):
        return FakeCollection(self._state, name)


class FakeClient:
    def __init__(self, state: dict[str, int]):
        self._state = state
        self.admin = SimpleNamespace(command=lambda _cmd: {"ok": 1})

    def __getitem__(self, _name: str):
        return FakeDatabase(self._state)

    def close(self):
        return None


def test_seed_runtime_data_skips_when_compatible_dataset_exists(monkeypatch):
    state = {
        "skills": 27,
        "dash_questions": 52,
        "generated_skills": 0,
        "scraped_questions": 0,
    }

    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setenv("MONGODB_DB_NAME", "ai_tutor")
    monkeypatch.setattr(seed_runtime_data, "MongoClient", lambda *args, **kwargs: FakeClient(state))
    monkeypatch.setattr(seed_runtime_data, "load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        seed_runtime_data,
        "run_legacy_seed",
        lambda: (_ for _ in ()).throw(AssertionError("seed step should be skipped")),
    )

    assert seed_runtime_data.main() == 0


def test_seed_runtime_data_populates_legacy_dataset_when_database_is_empty(monkeypatch):
    state = {
        "skills": 0,
        "dash_questions": 0,
        "generated_skills": 0,
        "scraped_questions": 0,
    }

    def fake_seed():
        state["skills"] = 27
        state["dash_questions"] = 52
        return True

    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setenv("MONGODB_DB_NAME", "ai_tutor")
    monkeypatch.setattr(seed_runtime_data, "MongoClient", lambda *args, **kwargs: FakeClient(state))
    monkeypatch.setattr(seed_runtime_data, "load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(seed_runtime_data, "run_legacy_seed", fake_seed)

    assert seed_runtime_data.main() == 0
