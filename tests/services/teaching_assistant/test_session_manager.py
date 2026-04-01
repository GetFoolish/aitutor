from datetime import datetime, timedelta
from types import SimpleNamespace

from services.TeachingAssistant.session_manager import SessionManager
from services.TeachingAssistant import session_manager as session_manager_module


class FakeUpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count


class FakeSessionsCollection:
    def __init__(self):
        self.docs = []
        self.indexes = []

    def create_index(self, spec, unique=False, expireAfterSeconds=None):
        self.indexes.append((spec, unique, expireAfterSeconds))

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find_one(self, query, projection=None):
        for doc in self.docs:
            if self._matches(doc, query):
                if projection:
                    return {key: doc[key] for key in projection if key in doc}
                return doc
        return None

    def find(self, query):
        return [doc for doc in self.docs if self._matches(doc, query)]

    def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                self._apply_update(doc, update, query)
                return FakeUpdateResult(1)
        return FakeUpdateResult(0)

    def update_many(self, query, update):
        count = 0
        for doc in self.docs:
            if self._matches(doc, query):
                self._apply_update(doc, update, query)
                count += 1
        return FakeUpdateResult(count)

    def _matches(self, doc, query):
        for key, value in query.items():
            if "." in key:
                first, second = key.split(".", 1)
                nested = doc.get(first, [])
                if not any(item.get(second) == value for item in nested):
                    return False
            elif doc.get(key) != value:
                return False
        return True

    def _apply_update(self, doc, update, query):
        for key, values in update.items():
            if key == "$set":
                for field, value in values.items():
                    if field.startswith("pending_instructions.$."):
                        instruction_id = query["pending_instructions.instruction_id"]
                        target_field = field.split(".", 2)[2]
                        for instruction in doc["pending_instructions"]:
                            if instruction["instruction_id"] == instruction_id:
                                instruction[target_field] = value
                    else:
                        doc[field] = value
            elif key == "$inc":
                for field, value in values.items():
                    doc[field] = doc.get(field, 0) + value
            elif key == "$push":
                for field, value in values.items():
                    doc.setdefault(field, []).append(value)


class FakeMongoClient:
    def __init__(self):
        self.db = SimpleNamespace(sessions=FakeSessionsCollection())


def create_manager():
    mongo = FakeMongoClient()
    manager = SessionManager(mongo)
    return manager, mongo.db.sessions


def test_session_manager_lifecycle(monkeypatch):
    manager, sessions = create_manager()
    now = datetime(2026, 3, 28, 12, 0, 0)
    monkeypatch.setattr(session_manager_module, "datetime", SimpleNamespace(utcnow=lambda: now))

    session = manager.create_session("user-123")
    session_id = session["session_id"]

    assert manager.get_active_session("user-123")["session_id"] == session_id
    assert len(manager.list_active_sessions()) == 1

    manager.update_activity(session_id)
    manager.record_conversation_turn(session_id)
    manager.record_question_answered(session_id, is_correct=True)
    instruction_id = manager.push_instruction(session_id, "Keep going")
    pending = manager.get_pending_instructions(session_id)

    assert len(pending) == 1
    assert pending[0]["instruction_id"] == instruction_id

    manager.mark_instruction_delivered(session_id, instruction_id)
    assert manager.get_pending_instructions(session_id) == []

    manager.set_connection_status(session_id, websocket=True, sse=True)
    info = manager.get_session_info(session_id)

    assert info["session_active"] is True
    assert info["questions_answered"] == 1
    assert info["questions_correct"] == 1
    assert info["websocket_connected"] is True
    assert info["sse_connected"] is True

    monkeypatch.setattr(session_manager_module, "datetime", SimpleNamespace(utcnow=lambda: now + timedelta(minutes=5)))
    summary = manager.end_session(session_id)

    assert summary["questions_answered"] == 1
    assert manager.get_session_info(session_id)["session_active"] is False


def test_session_manager_inactivity_and_bulk_end(monkeypatch):
    manager, sessions = create_manager()
    base_time = datetime(2026, 3, 28, 12, 0, 0)
    monkeypatch.setattr(session_manager_module, "datetime", SimpleNamespace(utcnow=lambda: base_time))

    first = manager.create_session("user-123")
    second = manager.create_session("user-123")

    assert manager.end_active_sessions("user-123") == 1

    sessions.docs.append(
        {
            "session_id": "sess_old",
            "user_id": "user-456",
            "started_at": base_time - timedelta(minutes=5),
            "last_activity": base_time - timedelta(minutes=5),
            "ended_at": None,
            "is_active": True,
            "questions_answered_this_session": 0,
            "questions_correct_this_session": 0,
            "last_conversation_turn": base_time - timedelta(minutes=3),
            "last_question_submission": base_time - timedelta(minutes=2),
            "pending_instructions": [],
            "websocket_connected": False,
            "sse_connected": False,
            "expires_at": base_time + timedelta(hours=24),
            "inactivity_prompt_sent": False,
        }
    )

    monkeypatch.setattr(session_manager_module, "datetime", SimpleNamespace(utcnow=lambda: base_time))
    assert manager.get_session_by_id(first["session_id"])["session_id"] == first["session_id"]
    assert manager.check_inactivity(second["session_id"]) is False

    monkeypatch.setattr(session_manager_module, "datetime", SimpleNamespace(utcnow=lambda: base_time + timedelta(minutes=6)))
    assert manager.check_inactivity("sess_old") is True
    assert manager.check_inactivity("sess_old") is False
    assert manager.get_session_info("missing") == {"session_active": False}
