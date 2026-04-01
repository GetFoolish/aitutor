from services.TeachingAssistant.greeting_handler import GreetingHandler


def test_greeting_handler_prompts_include_session_context():
    handler = GreetingHandler()

    assert "starting a tutoring session" in handler.get_greeting("user-123")
    assert "ending now" in handler.get_closing(12.5, 7)
    assert "continue" in handler.get_inactivity_prompt()
