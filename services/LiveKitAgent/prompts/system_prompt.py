"""
System Prompt Loading for AI Tutor Agent

Loads the Ms Davis tutor persona and Socratic method instructions
from the shared system prompt file.
"""

import os
from pathlib import Path


def load_system_prompt() -> str:
    """Load the AI Tutor system prompt from the markdown file.

    Looks for the system prompt in the frontend public folder.
    Falls back to a minimal prompt if file not found.

    Returns:
        The system prompt string for the AI tutor.
    """
    # Path relative to the services directory
    # services/LiveKitAgent/prompts/system_prompt.py -> frontend/public/ai_tutor_system_prompt.md
    current_dir = Path(__file__).parent
    prompt_path = current_dir.parent.parent.parent / "frontend" / "public" / "ai_tutor_system_prompt.md"

    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
            print(f"[SystemPrompt] Loaded from {prompt_path} ({len(prompt)} characters)")
            return prompt

    # Try alternative path (if running from different directory)
    alt_path = Path(os.getcwd()) / "frontend" / "public" / "ai_tutor_system_prompt.md"
    if alt_path.exists():
        with open(alt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
            print(f"[SystemPrompt] Loaded from {alt_path} ({len(prompt)} characters)")
            return prompt

    # Fallback minimal prompt
    print("[SystemPrompt] Warning: Could not find system prompt file, using fallback")
    return """You are Ms Davis, an expert AI Tutor. Your persona is that of an incredibly patient,
empathetic, and encouraging mentor. Your primary mission is to guide students to discover
answers for themselves, fostering critical thinking and genuine understanding.

You must NEVER give away the direct answer to a problem. Instead:
- Use the Socratic method - ask guiding questions
- Break problems down into smaller, fundamental steps
- Be warm, supportive, and non-judgmental
- Acknowledge and validate student work
- If a student is on the wrong track, use their mistake as a teaching opportunity

You can see the student's scratchpad where they work on problems. Reference their work
directly to show you're paying attention and guide their reasoning."""
