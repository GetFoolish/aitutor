import os
import sys
import json
from typing import List, Optional, Dict, Any
from google import genai
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.logging_config import get_logger
from .schema import Memory, MemoryType
from services.TeachingAssistant.prompts import get_memory_extraction_prompt

load_dotenv()

logger = get_logger(__name__)


class MemoryExtractor:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def extract_memories_batch(self, exchanges: List[Dict], student_id: str, session_id: str) -> Dict[str, Any]:
        """
        Extract memories and analyze exchanges in a single batch call.
        
        Args:
            exchanges: List of dicts with keys 'student_text', 'ai_text', 'topic'
            student_id: Student ID
            session_id: Session ID
            
        Returns:
            Dict containing:
            - memories: List of Memory objects
            - emotions: List of detected emotions
            - key_moments: List of key moments
            - unfinished_topics: List of unfinished topics
        """
        if not exchanges:
            logger.warning("extract_memories_batch called with empty exchanges list")
            return {"memories": [], "emotions": [], "key_moments": [], "unfinished_topics": []}

        logger.info(
            "Extracting memories and analyzing batch of %s exchanges for session %s",
            len(exchanges),
            session_id,
        )
        
        # Build the exchanges text for the prompt
        exchanges_text = ""
        for i, exchange in enumerate(exchanges, 1):
            exchanges_text += f"\n--- Exchange {i} ---\n"
            exchanges_text += f"Student: {exchange['student_text']}\n"
            exchanges_text += f"AI: {exchange['ai_text']}\n"
            exchanges_text += f"Topic: {exchange['topic']}\n"
        prompt = get_memory_extraction_prompt(len(exchanges), exchanges_text)

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt
            )
            
            # Track token usage for cost calculation
            try:
                from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                extract_and_track_tokens(response, session_id, "memory_extraction")
            except Exception as track_error:
                logger.debug(f"Token tracking failed (non-critical): {track_error}")
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            
            # Process memories
            memories = []
            for item in data.get("memories", []):
                memory = Memory(
                    type=MemoryType(item.get("type", "academic")),
                    text=item.get("text", ""),
                    importance=float(item.get("importance", 0.5)),
                    student_id=student_id,
                    session_id=session_id,
                    metadata=item.get("metadata", {})
                )
                memories.append(memory)
                
            result = {
                "memories": memories,
                "emotions": [e for e in data.get("emotions", []) if e and e != "neutral"],
                "key_moments": [k for k in data.get("key_moments", []) if k and k != "None"],
                "unfinished_topics": [t for t in data.get("unfinished_topics", []) if t and t != "None"]
            }

            # Detailed logging for memory extraction
            if len(memories) > 0:
                # Count by type
                memory_counts = {}
                for mem in memories:
                    mem_type = mem.type.value
                    memory_counts[mem_type] = memory_counts.get(mem_type, 0) + 1
                
                # Box-formatted extraction summary
                logger.info("╔" + "═" * 78 + "╗")
                logger.info("║ [MEMORY EXTRACTION] Batch Complete" + " " * 43 + "║")
                logger.info("╠" + "═" * 78 + "╣")
                logger.info("║ Exchanges Analyzed: %s%s║" % (len(exchanges), " " * (78 - 23 - len(str(len(exchanges))))))
                logger.info("║ Memories Extracted: %s (breakdown: %s)%s║" % (
                    len(memories),
                    memory_counts,
                    " " * (78 - 34 - len(str(len(memories))) - len(str(memory_counts)))
                ))
                logger.info("╠" + "═" * 78 + "╣")
                
                # Log each memory with type and importance
                for i, mem in enumerate(memories, 1):
                    emotion_str = mem.metadata.get('emotion', 'none')
                    safe_text = mem.text.encode("ascii", "replace").decode("ascii")
                    text_preview = safe_text[:60] + "..." if len(safe_text) > 60 else safe_text
                    
                    logger.info("║ [%s] (importance: %.2f, emotion: %s)%s║" % (
                        mem.type.value.upper(),
                        mem.importance,
                        emotion_str,
                        " " * max(0, 78 - 32 - len(mem.type.value) - len(emotion_str))
                    ))
                    logger.info("║ \"%s\"%s║" % (text_preview, " " * max(0, 78 - 4 - len(text_preview))))
                    
                    if i < len(memories):
                        logger.info("║%s║" % (" " * 78))
                
                logger.info("╚" + "═" * 78 + "╝")
            else:
                logger.info("[MEMORY_EXTRACTION] No memories extracted from %s exchanges", len(exchanges))
                
            if result["emotions"]:
                safe_emotions = [str(e).encode("ascii", "replace").decode("ascii") for e in result["emotions"]]
                logger.info("[MEMORY_EXTRACTION] Detected emotions: %s", safe_emotions)
            if result["key_moments"]:
                safe_moments = [str(k).encode("ascii", "replace").decode("ascii") for k in result["key_moments"]]
                logger.info("[MEMORY_EXTRACTION] Key moments: %s", safe_moments)
            if result["unfinished_topics"]:
                safe_topics = [str(t).encode("ascii", "replace").decode("ascii") for t in result["unfinished_topics"]]
                logger.info("[MEMORY_EXTRACTION] Unfinished topics: %s", safe_topics)
                
            return result
            
        except json.JSONDecodeError as e:
            logger.error("JSON decode error in batch memory extraction: %s", e)
            return {"memories": [], "emotions": [], "key_moments": [], "unfinished_topics": []}
        except Exception as e:
            logger.error("Error extracting memories from batch: %s", e, exc_info=True)
            return {"memories": [], "emotions": [], "key_moments": [], "unfinished_topics": []}

    def detect_emotion(self, text: str) -> Optional[str]:
        # Deprecated: Included in extract_memories_batch
        return None

    def detect_key_moments(self, student_text: str, ai_text: str, topic: str) -> Optional[str]:
        # Deprecated: Included in extract_memories_batch
        return None
            
    def detect_unfinished_topics(self, student_text: str, ai_text: str) -> Optional[str]:
        # Deprecated: Included in extract_memories_batch
        return None
