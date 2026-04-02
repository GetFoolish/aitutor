"""
Greeting Handler for TeachingAssistant
Simplified: Only generates greeting/closing prompts.
Session timing is now handled by SessionManager in MongoDB.
"""


class GreetingHandler:
    """
    Simplified: Only generates greeting/closing prompts.
    Session timing is now handled by SessionManager in MongoDB.
    """
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"

    def get_greeting(self, user_id: str) -> str:
        """Generate greeting prompt for session start"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
You are starting a tutoring session.
Please greet the student warmly and ask how they're doing today.
Make them feel welcome and excited to learn."""

    def get_closing(self, duration_minutes: float, questions_answered: int) -> str:
        """Generate closing prompt with session stats (passed in from SessionManager)"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
The tutoring session is ending now.
Session stats: {duration_minutes:.1f} minutes, {questions_answered} questions attempted.
Please give the student a warm closing message, acknowledge their hard work,
and encourage them for next session."""

    def get_inactivity_prompt(self) -> str:
        """Generate inactivity check prompt"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
Check with the student if they're there, and if they want to continue...
We have some very interesting problems to solve."""
