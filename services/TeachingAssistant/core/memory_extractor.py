"""
Memory Extractor - Extract individual facts from conversations
Based on the Cognitive Memory Pipeline architecture

This module handles:
- Extracting memories (facts) from conversation turns
- Classifying memory types (personal, academic, emotional)
- Scoring importance of memories
- Preparing memories for MongoDB and Pinecone storage

Supports: Google Gemini (primary) and OpenAI (fallback)
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Try Gemini first (primary)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Fallback to OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv

from ..models.memory import MemoryType, MemoryCreate, MemoryMetadata

load_dotenv()

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """
    Extracts individual memories (facts) from conversation transcripts.

    Memories are atomic facts that can be:
    - Stored in MongoDB for structured queries
    - Embedded and stored in Pinecone for semantic search
    - Used by the Biographer to update the biography

    Supports both Gemini (primary) and OpenAI (fallback).
    """

    def __init__(self):
        """
        Initialize the Memory Extractor.

        Tries Gemini first, falls back to OpenAI if not available.
        """
        self.enabled = False
        self.provider = None
        self.gemini_model = None
        self.openai_client = None

        # Try Gemini first
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_key)
                model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self.gemini_model = genai.GenerativeModel(model_name)
                self.enabled = True
                self.provider = "gemini"
                logger.info(f"[MEMORY_EXTRACTOR] Initialized with Gemini ({model_name})")
            except Exception as e:
                logger.warning(f"[MEMORY_EXTRACTOR] Gemini initialization failed: {e}")

        # Fallback to OpenAI
        if not self.enabled:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and OPENAI_AVAILABLE:
                try:
                    self.openai_client = OpenAI(api_key=openai_key)
                    self.enabled = True
                    self.provider = "openai"
                    logger.info("[MEMORY_EXTRACTOR] Initialized with OpenAI")
                except Exception as e:
                    logger.warning(f"[MEMORY_EXTRACTOR] OpenAI initialization failed: {e}")

        if not self.enabled:
            logger.warning("[MEMORY_EXTRACTOR] No LLM provider available. Using basic extraction.")

    def _call_llm(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        """Call the LLM with a prompt"""
        if not self.enabled:
            return None

        try:
            if self.provider == "gemini" and self.gemini_model:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=2000,
                    )
                )
                return response.text

            elif self.provider == "openai" and self.openai_client:
                kwargs = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.openai_client.chat.completions.create(**kwargs)
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] LLM call failed: {e}")
            return None

    def extract_memories(
        self,
        student_id: str,
        session_id: str,
        transcript: List[Dict[str, Any]]
    ) -> List[MemoryCreate]:
        """
        Extract memories from a conversation transcript.

        Args:
            student_id: The student's ID
            session_id: The session ID
            transcript: List of conversation turns

        Returns:
            List of MemoryCreate objects ready for storage
        """
        if not self.enabled:
            return self._extract_basic_memories(student_id, session_id, transcript)

        # Only extract from student turns
        student_turns = [
            turn for turn in transcript
            if turn.get("speaker") == "student"
        ]

        if not student_turns:
            return []

        # Format turns for the prompt
        turns_text = "\n".join([
            f"[{i}] Student: {turn['text']}"
            for i, turn in enumerate(student_turns)
        ])

        prompt = f"""Extract individual facts/memories from these student statements in a tutoring session.

Student statements:
{turns_text}

For each fact, provide:
1. The fact itself (as a concise statement)
2. Type: personal (interests, family, events), academic (learning progress), emotional (feelings, reactions), context (time, location), or commitment (promises made)
3. Importance: 0.0-1.0 (higher for formative experiences, lower for casual mentions)
4. Emotion: the emotion associated with this fact (if any)

Return as JSON array:
[
  {{"fact": "...", "type": "personal|academic|emotional|context|commitment", "importance": 0.0-1.0, "emotion": "...", "turn_index": 0}},
  ...
]

Only extract genuine facts - not conversational filler like "yes" or "okay".
Focus on information that helps understand who the student is.
Return ONLY the JSON array, no other text."""

        try:
            content = self._call_llm(prompt, json_mode=(self.provider == "openai"))

            if not content:
                return self._extract_basic_memories(student_id, session_id, transcript)

            # Parse JSON response
            try:
                # Clean response for Gemini (may have markdown)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                content = content.strip()

                # Handle both array and object responses
                data = json.loads(content)
                if isinstance(data, dict):
                    # Extract the array from various possible keys
                    facts = data.get("facts", data.get("memories", data.get("items", [])))
                else:
                    facts = data
            except json.JSONDecodeError as e:
                logger.error(f"[MEMORY_EXTRACTOR] Failed to parse JSON response: {e}")
                return self._extract_basic_memories(student_id, session_id, transcript)

            # Convert to MemoryCreate objects
            memories = []
            for fact in facts:
                if not fact.get("fact"):
                    continue

                memory_type = self._parse_memory_type(fact.get("type", "personal"))

                memories.append(MemoryCreate(
                    student_id=student_id,
                    session_id=session_id,
                    type=memory_type,
                    text=fact["fact"],
                    importance=min(1.0, max(0.0, float(fact.get("importance", 0.5)))),
                    metadata=MemoryMetadata(
                        emotion=fact.get("emotion"),
                        source_turn_index=fact.get("turn_index"),
                        confidence=0.8,  # LLM-extracted
                    )
                ))

            logger.info(f"[MEMORY_EXTRACTOR] Extracted {len(memories)} memories from session")
            return memories

        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] Extraction failed: {e}")
            return self._extract_basic_memories(student_id, session_id, transcript)

    def _parse_memory_type(self, type_str: str) -> MemoryType:
        """Parse memory type string to enum"""
        type_map = {
            "personal": MemoryType.PERSONAL,
            "academic": MemoryType.ACADEMIC,
            "emotional": MemoryType.EMOTIONAL,
            "context": MemoryType.CONTEXT,
            "commitment": MemoryType.COMMITMENT,
        }
        return type_map.get(type_str.lower(), MemoryType.PERSONAL)

    def _extract_basic_memories(
        self,
        student_id: str,
        session_id: str,
        transcript: List[Dict[str, Any]]
    ) -> List[MemoryCreate]:
        """
        Basic memory extraction without LLM (fallback).

        Simple keyword-based extraction for when LLM is unavailable.
        """
        memories = []

        # Keywords for different memory types
        personal_keywords = ["i like", "i love", "my favorite", "i enjoy", "my family", "my friend", "i play", "i want"]
        academic_keywords = ["i understand", "i learned", "i don't understand", "confused about", "makes sense"]
        emotional_keywords = ["i feel", "i'm feeling", "excited", "frustrated", "happy", "sad", "anxious", "worried"]

        for i, turn in enumerate(transcript):
            if turn.get("speaker") != "student":
                continue

            text = turn.get("text", "").lower()

            # Check for personal memories
            for keyword in personal_keywords:
                if keyword in text:
                    memories.append(MemoryCreate(
                        student_id=student_id,
                        session_id=session_id,
                        type=MemoryType.PERSONAL,
                        text=turn["text"],
                        importance=0.5,
                        metadata=MemoryMetadata(
                            source_turn_index=i,
                            confidence=0.5,  # Rule-based extraction
                        )
                    ))
                    break

            # Check for academic memories
            for keyword in academic_keywords:
                if keyword in text:
                    memories.append(MemoryCreate(
                        student_id=student_id,
                        session_id=session_id,
                        type=MemoryType.ACADEMIC,
                        text=turn["text"],
                        importance=0.6,
                        metadata=MemoryMetadata(
                            source_turn_index=i,
                            confidence=0.5,
                        )
                    ))
                    break

            # Check for emotional memories
            for keyword in emotional_keywords:
                if keyword in text:
                    memories.append(MemoryCreate(
                        student_id=student_id,
                        session_id=session_id,
                        type=MemoryType.EMOTIONAL,
                        text=turn["text"],
                        importance=0.6,
                        metadata=MemoryMetadata(
                            emotion=keyword.replace("i feel", "").replace("i'm feeling", "").strip() or "expressed",
                            source_turn_index=i,
                            confidence=0.5,
                        )
                    ))
                    break

        return memories

    def extract_topics(
        self,
        transcript: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract academic topics discussed in a session.

        Args:
            transcript: List of conversation turns

        Returns:
            List of topic strings
        """
        if not self.enabled:
            return ["General tutoring"]

        # Get all text
        all_text = " ".join([
            turn.get("text", "")
            for turn in transcript
        ])

        if len(all_text) < 50:
            return ["General tutoring"]

        prompt = f"""Extract the academic topics discussed in this tutoring session.

Conversation:
{all_text[:3000]}

Return ONLY a comma-separated list of specific math/academic topics discussed.
Examples: "Quadratic equations, Factoring, Discriminant"
If no specific topics, return "General discussion"."""

        try:
            content = self._call_llm(prompt)

            if not content:
                return ["General tutoring"]

            topics = [t.strip() for t in content.split(",") if t.strip()]
            return topics if topics else ["General discussion"]

        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] Topic extraction failed: {e}")
            return ["General tutoring"]

    def detect_breakthroughs(
        self,
        transcript: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect breakthrough moments in a session.

        Args:
            transcript: List of conversation turns

        Returns:
            List of breakthrough descriptions with timestamps
        """
        if not self.enabled:
            return []

        # Format transcript
        transcript_text = "\n".join([
            f"{turn.get('speaker', 'unknown').upper()}: {turn.get('text', '')}"
            for turn in transcript[-30:]  # Last 30 turns
        ])

        prompt = f"""Identify any breakthrough moments in this tutoring session.
A breakthrough is when the student:
- Suddenly understands a concept they were struggling with
- Makes a connection to something they care about
- Expresses confidence about a topic
- Has an "aha!" moment

Conversation:
{transcript_text}

Return as JSON array:
[
  {{"description": "Student understood quadratics by connecting to physics", "type": "conceptual|emotional|connection"}},
  ...
]

If no breakthroughs, return empty array: []
Return ONLY the JSON, no other text."""

        try:
            content = self._call_llm(prompt, json_mode=(self.provider == "openai"))

            if not content:
                return []

            # Clean response for Gemini
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            if isinstance(data, dict):
                return data.get("breakthroughs", data.get("items", []))
            return data if isinstance(data, list) else []

        except Exception as e:
            logger.error(f"[MEMORY_EXTRACTOR] Breakthrough detection failed: {e}")
            return []


# Singleton instance
memory_extractor = MemoryExtractor()
