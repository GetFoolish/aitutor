import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from .schema import Memory, MemoryType, ExtractedMemory

load_dotenv()


EXTRACTION_PROMPT = """Analyze this conversation exchange and extract memorable details about the student.

RULES:
1. Return [] for most exchanges - only extract genuinely useful information
2. DO NOT extract generic greetings or routine exchanges
3. Quality over quantity - one meaningful memory beats multiple low-value ones

Types to extract:
- academic: struggles, breakthroughs, explanations that worked
- personal: hobbies, pets, family, schedule, interests
- preference: communication style, pacing, emotional patterns
- context: significant session events, unfinished topics

Student: {student_text}
AI: {ai_text}
Current Topic: {topic}

Return JSON array. Each item needs:
- type: one of ["academic", "personal", "preference", "context"]
- text: concise memorable detail
- importance: 0-1 score
- metadata: ONLY include relevant fields (no nulls)

Metadata fields by type:
- academic: valence (struggle/breakthrough/neutral), emotion, resolution, topic
- personal: category (schedule/hobby/family/pets/interest), emotion
- preference: category (communication/pacing/format/emotional_response), trigger, response
- context: session_end (bool), emotion, next_topic

Return [] if nothing worth remembering.

Example output:
[
  {{
    "type": "academic",
    "text": "Student confused discriminant with coefficient, visual diagram helped",
    "importance": 0.8,
    "metadata": {{"valence": "struggle", "emotion": "frustrated", "resolution": "visual_helped", "topic": "quadratics"}}
  }},
  {{
    "type": "personal",
    "text": "Plays basketball on Fridays",
    "importance": 0.7,
    "metadata": {{"category": "hobby"}}
  }}
]"""


class MemoryExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self._model = None

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel('gemini-2.0-flash-lite')
        return self._model

    def extract_memories(
        self,
        student_text: str,
        ai_text: str,
        topic: str = "general",
        student_id: str = "unknown",
        session_id: Optional[str] = None
    ) -> List[Memory]:
        if not student_text or not student_text.strip():
            return []

        prompt = EXTRACTION_PROMPT.format(
            student_text=student_text,
            ai_text=ai_text or "",
            topic=topic
        )

        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            extracted = self._parse_response(response.text)

            memories = []
            for item in extracted:
                try:
                    mem_type = MemoryType(item['type'])
                    metadata = {k: v for k, v in item.get('metadata', {}).items() if v is not None}

                    memory = Memory(
                        student_id=student_id,
                        type=mem_type,
                        text=item['text'],
                        importance=item.get('importance', 0.5),
                        metadata=metadata,
                        session_id=session_id,
                        timestamp=datetime.utcnow()
                    )
                    memories.append(memory)
                except (ValueError, KeyError):
                    continue

            return memories

        except Exception as e:
            print(f"Memory extraction error: {e}")
            return []

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        text = response_text.strip()

        if text.startswith('```'):
            lines = text.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        return []

    def detect_emotion(self, text: str) -> Optional[str]:
        text_lower = text.lower()

        emotion_keywords = {
            'frustrated': ['frustrated', 'annoying', 'ugh', 'hate', 'stupid', 'dont get it', "don't get it"],
            'confused': ['confused', 'lost', 'what?', 'huh', "don't understand", 'dont understand', 'makes no sense'],
            'excited': ['excited', 'awesome', 'cool', 'yes!', 'got it', 'makes sense', 'oh!', 'finally'],
            'anxious': ['anxious', 'nervous', 'worried', 'stressed', 'scared', 'test', 'exam'],
            'tired': ['tired', 'exhausted', 'sleepy', 'long day', 'worn out'],
            'happy': ['happy', 'great', 'good', 'thanks', 'helpful', ':)', 'yay']
        }

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emotion

        return None


def detect_topic_shift(conversation: List[Dict[str, str]]) -> bool:
    if len(conversation) < 4:
        return False

    recent_text = ' '.join([
        turn.get('text', '') for turn in conversation[-4:]
    ]).lower()

    shift_indicators = [
        'let\'s move on', 'next topic', 'something else', 'different question',
        'change of topic', 'by the way', 'anyway', 'moving on'
    ]

    return any(indicator in recent_text for indicator in shift_indicators)


def has_past_reference(text: str) -> bool:
    text_lower = text.lower()

    past_indicators = [
        'like before', 'like last time', 'remember when', 'we did',
        'you said', 'you mentioned', 'earlier', 'yesterday', 'last session', 'last week'
    ]

    return any(indicator in text_lower for indicator in past_indicators)
