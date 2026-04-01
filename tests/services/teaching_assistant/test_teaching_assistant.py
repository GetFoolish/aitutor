from types import SimpleNamespace

from services.TeachingAssistant import teaching_assistant


class FakeSessionManager:
    def __init__(self):
        self.instructions = []

    def create_session(self, user_id):
        return {"session_id": "sess-123"}

    def get_session_info(self, session_id):
        return {"session_id": session_id, "session_active": True}

    def end_session(self, session_id):
        if session_id == "missing":
            return {}
        return {"session_id": session_id, "duration_minutes": 12.5, "questions_answered": 4}

    def record_question_answered(self, session_id, is_correct):
        self.last_question = (session_id, is_correct)

    def record_conversation_turn(self, session_id):
        self.last_turn = session_id

    def check_inactivity(self, session_id):
        return session_id == "inactive"

    def push_instruction(self, session_id, instruction):
        self.instructions.append((session_id, instruction))
        return "instr-123"

    def get_active_session(self, user_id):
        return {"session_id": "sess-123", "user_id": user_id}


class FakeGreetingHandler:
    def get_greeting(self, user_id):
        return f"hello {user_id}"

    def get_closing(self, duration_minutes, questions_answered):
        return f"bye after {duration_minutes} / {questions_answered}"

    def get_inactivity_prompt(self):
        return "still there?"


def test_teaching_assistant_orchestrates_session_flow(monkeypatch):
    fake_session_manager = FakeSessionManager()
    monkeypatch.setattr(teaching_assistant, "MongoDBManager", lambda: object())
    monkeypatch.setattr(teaching_assistant, "SessionManager", lambda mongo: fake_session_manager)
    monkeypatch.setattr(teaching_assistant, "GreetingHandler", lambda: FakeGreetingHandler())

    assistant = teaching_assistant.TeachingAssistant()

    started = assistant.start_session("user-123")
    assistant.record_question_answered("sess-123", "question-1", True)
    assistant.record_conversation_turn("sess-123")
    inactive_prompt = assistant.check_inactivity("inactive")
    missing_prompt = assistant.check_inactivity("active")
    ended = assistant.end_session("sess-123")
    missing_end = assistant.end_session("missing")

    assert started == {
        "session_id": "sess-123",
        "prompt": "hello user-123",
        "session_info": {"session_id": "sess-123", "session_active": True},
    }
    assert fake_session_manager.last_question == ("sess-123", True)
    assert fake_session_manager.last_turn == "sess-123"
    assert inactive_prompt == "still there?"
    assert missing_prompt is None
    assert fake_session_manager.instructions == [("inactive", "still there?")]
    assert ended == {
        "prompt": "bye after 12.5 / 4",
        "session_info": {"session_id": "sess-123", "duration_minutes": 12.5, "questions_answered": 4},
    }
    assert missing_end == {"prompt": "", "session_info": {"session_active": False}}
    assert assistant.get_session_info("sess-123") == {"session_id": "sess-123", "session_active": True}
    assert assistant.get_active_session("user-123") == {"session_id": "sess-123", "user_id": "user-123"}
    assert assistant.push_instruction("sess-123", "manual") == "instr-123"
