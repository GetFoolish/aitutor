"""
Memory Extractor - Extract memories from conversation exchanges using LLM
Based on v4 teaching-assistant branch implementation with Gemini support

Features:
- Batch extraction from conversation turns
- Memory classification (academic, personal, preference, context, emotional)
- Emotion detection
- Breakthrough/struggle moment identification
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

# Try to use shared logging config for colored output
try:
    from shared.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Try Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .schema import Memory, MemoryType


class MemoryExtractor:
    """
    Extracts memories from student-tutor conversation exchanges.

    Uses LLM to identify:
    - Academic memories (learning progress, understanding)
    - Personal memories (interests, family, events)
    - Preference memories (likes, dislikes, learning style)
    - Context memories (time, location, circumstances)
    - Emotional memories (feelings, reactions)
    """

    def __init__(self):
        self.enabled = False
        self._gemini_model = None

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_key)
                model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self._gemini_model = genai.GenerativeModel(model_name)
                self.enabled = True
                logger.info(f"[MEMORY_EXTRACTOR] Initialized with Gemini ({model_name})")
            except Exception as e:
                logger.warning(f"[MEMORY_EXTRACTOR] Gemini init failed: {e}")

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call Gemini LLM"""
        if not self.enabled:
            return None

        try:
            response = self._gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] LLM call failed: {e}")
            return None

    def extract_memories_batch(
        self,
        student_id: str,
        session_id: str,
        exchanges: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Extract memories from a batch of conversation exchanges.

        Args:
            student_id: Student ID
            session_id: Session ID
            exchanges: List of {student: "...", tutor: "..."} exchanges

        Returns:
            Dict with:
                - memories: List[Memory]
                - emotions: List[str] detected emotions
                - breakthroughs: List[str] breakthrough moments
                - unfinished_topics: List[str] topics to continue
        """
        result = {
            "memories": [],
            "emotions": [],
            "breakthroughs": [],
            "unfinished_topics": []
        }

        if not self.enabled or not exchanges:
            return result

        # Format exchanges for prompt
        exchanges_text = ""
        for i, ex in enumerate(exchanges[-20:]):  # Limit to last 20
            student_text = ex.get("student", ex.get("user", ""))
            tutor_text = ex.get("tutor", ex.get("adam", ""))
            exchanges_text += f"[Turn {i+1}]\nSTUDENT: {student_text}\nTUTOR: {tutor_text}\n\n"

        prompt = f"""Analyze these {len(exchanges[-20:])} conversation exchanges to update the Student Profile.

{exchanges_text}

Task 1: Extract STUDENT MEMORIES.
**GOLDEN RULE**: You are recording PERMANENT FACTS about the Student. You are NOT summarizing a conversation.

1. **STRICT PROHIBITION (Zero Tolerance)**:
   - **NEVER** mention "The AI", "The Tutor", "The System", "The Assistant", or "The Conversation".
   - **NEVER** output meta-commentary like "Student responded to the prompt" or "Student interacted with the system".
   - **BAD Example**: "Student asked the AI for help with algebra."
   - **GOOD Example**: "Student requested help with algebra."
   - **BAD Example**: "Student answered the AI correctly."
   - **GOOD Example**: "Student demonstrated mastery of [specific concept]."

2. **CRITICAL TRANSCRIPTION HANDLING (Audio Artifacts)**:
   - The "Student" text comes from realtime audio-to-text. It may contain broken words (e.g., "Cu rrent ly", "chem is try").
   - **REPAIR**: You MUST mentally repair these fragments to capture the INTENT (e.g. treat "chem is try" as "chemistry").
   - **NO META-MEMORIES**: DO NOT record memories about the text format (e.g., "Student types with spaces" -> DELETE THIS).
   - **IGNORE GARBAGE**: If text is unintelligible, IGNORE IT. Do not record "Student text is unclear".

3. **CATEGORIES**:
   - **Academic**: Knowledge gaps, misconceptions, or mastery (e.g., "Understands chain rule", "Confused by integrals").
   - **Personal**: Hobbies, life details (e.g., "Plays soccer", "Has a dog named Max").
   - **Preference**: Learning needs (e.g., "Prefers visual examples", "Dislikes long lectures").
   - **Context**: Emotional state (e.g., "Anxious about upcoming exam").
   - **Emotional**: Feelings and reactions captured during session.

Task 2: Detect EMOTIONS (frustrated, confused, excited, anxious, tired, happy, engaged, curious, bored, confident, nervous, or neutral).
Task 3: Identify BREAKTHROUGHS - Moments of understanding or connection.
Task 4: Identify UNFINISHED_TOPICS - Topics that need follow-up.

Return JSON:
{{
  "memories": [
    {{"text": "...", "type": "academic|personal|preference|context|emotional", "importance": 0.0-1.0, "emotion": "..."}}
  ],
  "emotions": ["emotion1", "emotion2"],
  "breakthroughs": ["Student understood X by connecting to Y"],
  "unfinished_topics": ["Topic that needs follow-up"]
}}

Return ONLY valid JSON, no other text."""

        try:
            content = self._call_llm(prompt)
            if not content:
                return result

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # Convert to Memory objects
            current_time = time.time()
            for mem_data in data.get("memories", []):
                if not mem_data.get("text"):
                    continue

                try:
                    mem_type_str = mem_data.get("type", "personal").lower()
                    mem_type = MemoryType(mem_type_str) if mem_type_str in [e.value for e in MemoryType] else MemoryType.PERSONAL

                    memory = Memory(
                        student_id=student_id,
                        session_id=session_id,
                        type=mem_type,
                        text=mem_data["text"],
                        importance=min(1.0, max(0.0, float(mem_data.get("importance", 0.5)))),
                        timestamp=datetime.utcnow(),
                        first_epoch=current_time,
                        last_epoch=current_time,
                        metadata={
                            "emotion": mem_data.get("emotion"),
                            "extraction_method": "llm_batch"
                        }
                    )
                    result["memories"].append(memory)
                except Exception as e:
                    logger.error(f"[MEMORY_EXTRACTOR] Error creating memory: {e}")

            result["emotions"] = data.get("emotions", [])
            result["breakthroughs"] = data.get("breakthroughs", [])
            result["unfinished_topics"] = data.get("unfinished_topics", [])

            # Log extraction stats
            type_counts = {}
            for mem in result["memories"]:
                type_counts[mem.type.value] = type_counts.get(mem.type.value, 0) + 1

            logger.info(
                f"[MEMORY_EXTRACTOR] Extracted {len(result['memories'])} memories "
                f"(breakdown: {type_counts}), {len(result['emotions'])} emotions, "
                f"{len(result['breakthroughs'])} breakthroughs"
            )

        except json.JSONDecodeError as e:
            logger.error(f"[MEMORY_EXTRACTOR] JSON parse error: {e}")
        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] Extraction failed: {e}")

        return result

    def extract_single_turn(
        self,
        student_id: str,
        session_id: str,
        student_text: str,
        tutor_text: str = ""
    ) -> List[Memory]:
        """
        Extract memories from a single conversation turn.

        Args:
            student_id: Student ID
            session_id: Session ID
            student_text: What the student said
            tutor_text: What the tutor said (for context)

        Returns:
            List of Memory objects
        """
        result = self.extract_memories_batch(
            student_id=student_id,
            session_id=session_id,
            exchanges=[{"student": student_text, "tutor": tutor_text}]
        )
        return result.get("memories", [])

    def detect_emotions(self, text: str) -> List[str]:
        """
        Detect emotions in text.

        Args:
            text: Text to analyze

        Returns:
            List of detected emotions
        """
        if not self.enabled or not text:
            return []

        prompt = f"""Analyze this student statement for emotions.

Text: "{text[:500]}"

Return ONLY a comma-separated list of emotions from:
frustrated, confused, excited, anxious, tired, happy, engaged, curious, bored, confident, nervous

If no clear emotion, return: neutral"""

        try:
            result = self._call_llm(prompt)
            if result:
                emotions = [e.strip().lower() for e in result.split(",")]
                return [e for e in emotions if e and e != "neutral"]
        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] Emotion detection failed: {e}")

        return []

    def identify_breakthroughs(
        self,
        exchanges: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Identify breakthrough moments in conversation.

        Args:
            exchanges: List of conversation exchanges

        Returns:
            List of breakthrough descriptions
        """
        if not self.enabled or not exchanges:
            return []

        exchanges_text = "\n".join([
            f"STUDENT: {ex.get('student', '')}\nTUTOR: {ex.get('tutor', '')}"
            for ex in exchanges[-15:]
        ])

        prompt = f"""Identify breakthrough moments in this tutoring session.

A breakthrough is when the student:
- Suddenly understands a concept
- Makes a connection to something personal
- Shows increased confidence
- Has an "aha!" moment

Conversation:
{exchanges_text}

Return JSON array:
[{{"description": "...", "type": "conceptual|emotional|connection"}}]

If no breakthroughs, return: []"""

        try:
            content = self._call_llm(prompt)
            if content:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return json.loads(content.strip())
        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] Breakthrough detection failed: {e}")

        return []


# Singleton instance
memory_extractor = MemoryExtractor()
