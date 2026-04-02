from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import services.TeachingAssistant.greeting_handler as greeting_handler
import services.TeachingAssistant.session_manager as session_manager
import services.TeachingAssistant.teaching_assistant as teaching_assistant


class FakeSessionsCollection:
    def __init__(self):
        self.docs = {}
        self.indexes = []

    def create_index(self, spec, **kwargs):
        self.indexes.append((spec, kwargs))

    def _matches(self, doc, query):
        for key, value in query.items():
            if key == "pending_instructions.instruction_id":
                if not any(item["instruction_id"] == value for item in doc.get("pending_instructions", [])):
                    return False
            elif doc.get(key) != value:
                return False
        return True

    def insert_one(self, document):
        self.docs[document["session_id"]] = deepcopy(document)
        return SimpleNamespace(inserted_id=document["session_id"])

    def find_one(self, query, projection=None):
        for document in self.docs.values():
            if self._matches(document, query):
                if projection:
                    projected = {}
                    for key, enabled in projection.items():
                        if enabled and key in document:
                            projected[key] = deepcopy(document[key])
                    return projected
                return deepcopy(document)
        return None

    def find(self, query):
        return [deepcopy(document) for document in self.docs.values() if self._matches(document, query)]

    def update_one(self, query, update):
        for session_id, document in self.docs.items():
            if not self._matches(document, query):
                continue
            for key, value in update.get("$set", {}).items():
                if key == "pending_instructions.$.delivered":
                    instruction_id = query["pending_instructions.instruction_id"]
                    for item in document["pending_instructions"]:
                        if item["instruction_id"] == instruction_id:
                            item["delivered"] = value
                else:
                    document[key] = value
            for key, value in update.get("$inc", {}).items():
                document[key] = document.get(key, 0) + value
            for key, value in update.get("$push", {}).items():
                document.setdefault(key, []).append(value)
            self.docs[session_id] = document
            return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)

    def update_many(self, query, update):
        modified = 0
        for session_id, document in self.docs.items():
            if not self._matches(document, query):
                continue
            for key, value in update.get("$set", {}).items():
                document[key] = value
            self.docs[session_id] = document
            modified += 1
        return SimpleNamespace(modified_count=modified)


def build_session_manager():
    collection = FakeSessionsCollection()
    mongo = SimpleNamespace(db=SimpleNamespace(sessions=collection))
    return session_manager.SessionManager(mongo), collection


def test_greeting_handler_returns_expected_prompts():
    handler = greeting_handler.GreetingHandler()

    assert "starting a tutoring session" in handler.get_greeting("user-123")
    assert "2 questions attempted" in handler.get_closing(12.3, 2)
    assert "Check with the student if they're there" in handler.get_inactivity_prompt()


def test_session_manager_full_lifecycle():
    manager, collection = build_session_manager()

    created = manager.create_session("user-123")
    session_id = created["session_id"]

    assert len(collection.indexes) == 3
    assert manager.get_active_session("user-123")["session_id"] == session_id
    assert manager.get_session_by_id(session_id)["session_id"] == session_id
    assert manager.list_active_sessions()[0]["session_id"] == session_id

    manager.update_activity(session_id)
    manager.record_conversation_turn(session_id)
    manager.record_question_answered(session_id, is_correct=True)
    manager.record_question_answered(session_id, is_correct=False)

    instruction_id = manager.push_instruction(session_id, "Keep going")
    pending = manager.get_pending_instructions(session_id)
    assert pending[0]["instruction_id"] == instruction_id

    manager.mark_instruction_delivered(session_id, instruction_id)
    assert manager.get_pending_instructions(session_id) == []

    manager.set_connection_status(session_id, websocket=True, sse=True)
    info = manager.get_session_info(session_id)
    assert info["session_active"] is True
    assert info["questions_answered"] == 2
    assert info["questions_correct"] == 1
    assert info["websocket_connected"] is True
    assert info["sse_connected"] is True

    collection.docs[session_id]["started_at"] = datetime.utcnow() - timedelta(minutes=2)
    collection.docs[session_id]["last_conversation_turn"] = datetime.utcnow() - timedelta(minutes=2)
    collection.docs[session_id]["last_question_submission"] = datetime.utcnow() - timedelta(minutes=2)

    assert manager.check_inactivity(session_id) is True
    assert manager.check_inactivity(session_id) is False

    summary = manager.end_session(session_id)
    assert summary["session_id"] == session_id
    assert summary["questions_answered"] == 2
    assert summary["questions_correct"] == 1
    assert manager.get_session_info(session_id)["session_active"] is False


def test_session_manager_end_active_sessions_and_missing_cases():
    manager, collection = build_session_manager()

    first = manager.create_session("user-123")
    second = manager.create_session("user-123")

    assert manager.end_active_sessions("user-123") == 1
    assert manager.get_pending_instructions("missing") == []
    assert manager.end_session("missing") == {}
    assert manager.get_session_info("missing") == {"session_active": False}

    collection.docs[second["session_id"]]["is_active"] = False
    assert manager.check_inactivity(second["session_id"]) is False
    assert manager.get_active_session("user-123") is None


def test_teaching_assistant_wires_session_manager_and_greeting_handler(monkeypatch):
    fake_session_manager = SimpleNamespace(
        create_session=lambda user_id: {"session_id": "sess-1"},
        get_session_info=lambda session_id: {"session_id": session_id, "session_active": True},
        end_session=lambda session_id: {"session_id": session_id, "duration_minutes": 3.5, "questions_answered": 4},
        record_question_answered=lambda session_id, is_correct: None,
        record_conversation_turn=lambda session_id: None,
        check_inactivity=lambda session_id: True,
        push_instruction=lambda session_id, instruction: "instr-1",
        get_active_session=lambda user_id: {"session_id": "sess-1"},
    )

    class FakeGreetingSkill:
        name = "greeting"
        def get_closing(self, duration_minutes, questions_answered):
            return f"bye {duration_minutes}/{questions_answered}"
        def get_inactivity_prompt(self):
            return "are you there?"

    class FakeSkillsManager:
        skills = [FakeGreetingSkill()]
        def execute_skills(self, context):
            return []

    fake_context_manager = SimpleNamespace(
        create_context=lambda *a, **kw: None,
        get_context=lambda *a, **kw: None,
        sync_dirty_contexts=lambda: None,
        cleanup_stale_contexts=lambda: None,
    )
    fake_memory_extractor = SimpleNamespace(
        extract_memories_batch=lambda *a, **kw: {"memories": [], "emotions": [], "key_moments": [], "unfinished_topics": []},
    )

    monkeypatch.setattr(teaching_assistant, "MongoDBManager", lambda: SimpleNamespace(db=SimpleNamespace()))
    monkeypatch.setattr(teaching_assistant, "SessionManager", lambda mongo, config=None: fake_session_manager)
    monkeypatch.setattr(teaching_assistant, "ContextManager", lambda mongo, config=None: fake_context_manager)
    monkeypatch.setattr(teaching_assistant, "MemoryExtractor", lambda: fake_memory_extractor)
    monkeypatch.setattr(teaching_assistant, "SkillsManager", lambda skills_dir, config=None: FakeSkillsManager())

    assistant = teaching_assistant.TeachingAssistant(session_manager=fake_session_manager)

    started = assistant.start_session("user-123")
    assert started == {
        "session_id": "sess-1",
        "prompt": "",
        "session_info": {"session_id": "sess-1", "session_active": True},
    }

    ended = assistant.end_session("sess-1")
    assert ended["prompt"] == "bye 3.5/4"
    assert assistant.check_inactivity("sess-1") == "are you there?"
    assert assistant.get_session_info("sess-1") == {"session_id": "sess-1", "session_active": True}
    assert assistant.get_active_session("user-123") == {"session_id": "sess-1"}
    assert assistant.push_instruction("sess-1", "nudge") == "instr-1"
