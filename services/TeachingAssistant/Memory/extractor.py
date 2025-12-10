import os
import json
import logging
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from .schema import Memory, MemoryType

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)


class MemoryExtractor:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def extract_memories(self, student_text: str, ai_text: str, topic: str, 
                        student_id: str, session_id: str) -> List[Memory]:
        logger.info(f"🔍 Extracting memories for session {session_id}")
        
        prompt = f"""Extract memorable details from this conversation exchange. Extract ALL types of memories that are worth remembering:
- ACADEMIC: Learning progress, concepts understood, mistakes made, skills demonstrated
- PERSONAL: Personal information shared, family, hobbies, interests, background
- PREFERENCE: Learning style, communication preferences, what they like/dislike
- CONTEXT: Conversation context, session-specific details, ongoing topics

Return only genuinely useful information as JSON array. Return empty array if nothing worth remembering.

Student: {student_text}
AI: {ai_text}
Topic: {topic}

Return JSON array with format (extract multiple memories if applicable):
[
  {{
    "type": "academic|personal|preference|context",
    "text": "memorable detail",
    "importance": 0.0-1.0,
    "metadata": {{
      "emotion": "frustrated|confused|excited|anxious|tired|happy",
      "valence": "positive|negative|neutral",
      "category": "category name",
      "topic": "topic name"
    }}
  }}
]

IMPORTANT: Extract memories of ALL 4 types if present. Don't limit to just one type."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
            memories = []
            for item in data:
                memory = Memory(
                    type=MemoryType(item.get("type", "academic")),
                    text=item.get("text", ""),
                    importance=float(item.get("importance", 0.5)),
                    student_id=student_id,
                    session_id=session_id,
                    metadata=item.get("metadata", {})
                )
                memories.append(memory)
            
            memory_types = [m.type.value for m in memories]
            type_counts = {}
            for mt in memory_types:
                type_counts[mt] = type_counts.get(mt, 0) + 1
            
            if len(memories) > 0:
                logger.info(f"✅ Extracted {len(memories)} memories: {type_counts}")
            return memories
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error in memory extraction: {e}")
            logger.error(f"Response text: {text[:500] if 'text' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"❌ Error extracting memories: {type(e).__name__}: {e}", exc_info=True)
            return []

    def detect_emotion(self, text: str) -> Optional[str]:
        valid_emotions = ["frustrated", "confused", "excited", "anxious", "tired", "happy"]
        prompt = f"""Detect the emotion in this text. Return one word only: {', '.join(valid_emotions)} or None.

Text: {text}"""

        try:
            response = self.model.generate_content(prompt)
            emotion = response.text.strip().lower()
            return emotion if emotion in valid_emotions else None
        except Exception as e:
            logger.warning(f"Error detecting emotion: {e}")
            return None

