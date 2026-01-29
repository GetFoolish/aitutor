#!/usr/bin/env python3
"""
Memory-Aware Question Personalizer

Uses user memories to make questions personal and relatable.
- If user loves dinosaurs → dinosaur math problems
- If user has a dog named Buddy → "Buddy has 3 bones..."
- If user struggles with fractions → extra gentle hints

Integrates with v1-memory branch's Memory system (MemoryRetriever, MemoryStore).
"""

import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services" / "TeachingAssistant"))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient

# Try to import v1-memory components
try:
    from Memory.schema import Memory, MemoryType
    from Memory.vector_store import MemoryStore, MemoryConfig
    from Memory.retriever import MemoryRetriever
    MEMORY_SYSTEM_AVAILABLE = True
except ImportError:
    MEMORY_SYSTEM_AVAILABLE = False
    print("[memory_personalizer] v1-memory system not available, using MongoDB fallback")


@dataclass
class UserMemory:
    """A user memory for personalization."""
    type: str  # personal, preference, academic, emotional
    text: str
    importance: float


@dataclass 
class PersonalizationContext:
    """Context for personalizing questions."""
    user_id: str
    interests: List[str]  # dinosaurs, space, football...
    pets: List[Dict[str, str]]  # [{"type": "dog", "name": "Buddy"}]
    family: List[Dict[str, str]]  # [{"relation": "sister", "name": "Emma"}]
    favorite_things: List[str]  # colors, foods, games...
    struggles: List[str]  # math topics they find hard
    strengths: List[str]  # what they're good at
    emotional_context: List[str]  # how they feel about learning
    

class MemoryPersonalizer:
    """Retrieves and formats user memories for question personalization.
    
    Uses v1-memory system (MemoryStore/MemoryRetriever) when available,
    falls back to direct MongoDB queries otherwise.
    """
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        self.uri = mongodb_uri or os.getenv("MONGODB_URI")
        if not self.uri:
            raise ValueError("MONGODB_URI not set")
        
        self.client = MongoClient(self.uri)
        self.db = self.client["ai_tutor"]
        
        # Initialize v1-memory system if available
        self.memory_store = None
        self.memory_retriever = None
        if MEMORY_SYSTEM_AVAILABLE:
            try:
                config = MemoryConfig(
                    mongodb_uri=self.uri,
                    collection_name="memory_vectors"
                )
                self.memory_store = MemoryStore(config)
                self.memory_retriever = MemoryRetriever(self.memory_store)
                print("[memory_personalizer] v1-memory system initialized")
            except Exception as e:
                print(f"[memory_personalizer] v1-memory init failed: {e}")
        
    def get_user_memories(self, user_id: str, limit: int = 50) -> List[UserMemory]:
        """Get all memories for a user.
        
        Uses v1-memory vector store when available for semantic retrieval,
        falls back to MongoDB direct queries.
        """
        memories = []
        
        # Try v1-memory system first (semantic/vector retrieval)
        if self.memory_store:
            try:
                # Get memories by type for comprehensive coverage
                for mem_type in [MemoryType.PERSONAL, MemoryType.PREFERENCE, 
                                MemoryType.ACADEMIC, MemoryType.EMOTIONAL]:
                    results = self.memory_store.get_by_type(user_id, mem_type, limit=limit//4)
                    for mem in results:
                        memories.append(UserMemory(
                            type=mem.type.value if hasattr(mem.type, 'value') else str(mem.type),
                            text=mem.text,
                            importance=mem.importance
                        ))
                if memories:
                    print(f"[memory_personalizer] Retrieved {len(memories)} memories via v1-memory system")
                    return memories
            except Exception as e:
                print(f"[memory_personalizer] v1-memory retrieval failed: {e}")
        
        # Fallback: Direct MongoDB queries
        # Try memories collection
        for doc in self.db.memories.find({"student_id": user_id}).limit(limit):
            memories.append(UserMemory(
                type=doc.get("type", "personal"),
                text=doc.get("text", ""),
                importance=doc.get("importance", 0.5)
            ))
        
        # Also check user_memories collection
        for doc in self.db.user_memories.find({"user_id": user_id}).limit(limit):
            memories.append(UserMemory(
                type=doc.get("memory_type", "personal"),
                text=doc.get("content", doc.get("text", "")),
                importance=doc.get("importance", 0.5)
            ))
        
        print(f"[memory_personalizer] Retrieved {len(memories)} memories via MongoDB")
        return memories
    
    def get_relevant_memories(self, user_id: str, topic: str, limit: int = 10) -> List[UserMemory]:
        """Get memories relevant to a specific topic using semantic search.
        
        e.g., topic="addition" might retrieve "struggles with carrying numbers"
        """
        memories = []
        
        if self.memory_store:
            try:
                # Semantic search using v1-memory vector store
                results = self.memory_store.search(
                    user_id=user_id,
                    query=topic,
                    top_k=limit
                )
                for result in results:
                    mem = result.get("memory") or result
                    memories.append(UserMemory(
                        type=getattr(mem, 'type', 'personal'),
                        text=getattr(mem, 'text', str(mem)),
                        importance=getattr(mem, 'importance', result.get("score", 0.5))
                    ))
                print(f"[memory_personalizer] Semantic search for '{topic}': {len(memories)} results")
            except Exception as e:
                print(f"[memory_personalizer] Semantic search failed: {e}")
        
        return memories
    
    def build_personalization_context(self, user_id: str) -> PersonalizationContext:
        """Build a rich personalization context from user memories."""
        memories = self.get_user_memories(user_id)
        
        context = PersonalizationContext(
            user_id=user_id,
            interests=[],
            pets=[],
            family=[],
            favorite_things=[],
            struggles=[],
            strengths=[],
            emotional_context=[]
        )
        
        # Parse memories into categories
        for mem in memories:
            text_lower = mem.text.lower()
            
            # Extract interests
            interest_keywords = ["loves", "likes", "interested in", "enjoys", "favorite", "obsessed with"]
            for kw in interest_keywords:
                if kw in text_lower:
                    context.interests.append(mem.text)
                    break
            
            # Extract pets
            pet_keywords = ["dog", "cat", "pet", "puppy", "kitten", "fish", "hamster", "rabbit"]
            for pet in pet_keywords:
                if pet in text_lower:
                    context.pets.append({"type": pet, "mention": mem.text})
                    break
            
            # Extract family
            family_keywords = ["brother", "sister", "mom", "dad", "parent", "grandma", "grandpa", "cousin"]
            for fam in family_keywords:
                if fam in text_lower:
                    context.family.append({"relation": fam, "mention": mem.text})
                    break
            
            # Extract struggles (academic)
            if mem.type == "academic" and any(w in text_lower for w in ["struggle", "difficult", "hard", "confused", "trouble"]):
                context.struggles.append(mem.text)
            
            # Extract strengths
            if any(w in text_lower for w in ["good at", "loves doing", "easy for", "strong in", "excels"]):
                context.strengths.append(mem.text)
            
            # Emotional context
            if mem.type == "emotional":
                context.emotional_context.append(mem.text)
        
        return context
    
    def get_personalization_prompt(self, user_id: str) -> str:
        """Get a prompt section for personalizing questions based on user memories."""
        context = self.build_personalization_context(user_id)
        
        prompt_parts = ["USER MEMORIES (use these to personalize questions):\n"]
        
        if context.interests:
            prompt_parts.append("interests/likes:")
            for interest in context.interests[:5]:
                prompt_parts.append(f"  - {interest}")
        
        if context.pets:
            prompt_parts.append("\npets:")
            for pet in context.pets[:3]:
                prompt_parts.append(f"  - {pet['mention']}")
        
        if context.family:
            prompt_parts.append("\nfamily:")
            for fam in context.family[:3]:
                prompt_parts.append(f"  - {fam['mention']}")
        
        if context.struggles:
            prompt_parts.append("\nthings they find tricky (be extra gentle here):")
            for struggle in context.struggles[:3]:
                prompt_parts.append(f"  - {struggle}")
        
        if context.strengths:
            prompt_parts.append("\nthings they're good at (can reference these for confidence):")
            for strength in context.strengths[:3]:
                prompt_parts.append(f"  - {strength}")
        
        if context.emotional_context:
            prompt_parts.append("\nhow they're feeling:")
            for emo in context.emotional_context[:2]:
                prompt_parts.append(f"  - {emo}")
        
        prompt_parts.append("""
---
PERSONALIZATION INSTRUCTIONS:
- use their interests in word problems (if they like dinosaurs, use dinosaurs)
- if they have a pet, use the pet's name in examples
- if they struggle with something, add extra encouragement
- make it feel like you know them
- keep the innocent drinks tone - casual, friendly, personal

example:
  if memory says "loves dinosaurs" and "has a dog called Rex"
  instead of: "you have 3 apples..."
  write: "so rex the dinosaur-loving dog has found 3 bones..."
""")
        
        return "\n".join(prompt_parts)


def generate_personalized_question_prompt(
    user_id: str,
    base_prompt: str,
    widget_type: str = None,
    topic: str = None,
    grade_level: str = "K-2"
) -> str:
    """
    Generate a complete prompt for personalized question generation.
    
    Combines:
    - User memories for personalization (interests, pets, struggles)
    - Topic-relevant memories (semantic search)
    - Tone guidelines (innocent drinks style)
    - Widget type examples from DB
    
    Args:
        user_id: User to personalize for
        base_prompt: The generation request
        widget_type: Type of widget (radio, numeric-input, etc.)
        topic: Math topic for relevant memory search (addition, fractions, etc.)
        grade_level: K-2, 3-5, 6-8, 9-12
    """
    # Import from same directory
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    from tone_guidelines import get_tone_prompt
    from example_retriever import ExampleRetriever
    
    personalizer = MemoryPersonalizer()
    
    # Get user memories (general)
    memory_prompt = personalizer.get_personalization_prompt(user_id)
    
    # Get topic-relevant memories if topic specified
    topic_memories_prompt = ""
    if topic:
        relevant = personalizer.get_relevant_memories(user_id, topic, limit=5)
        if relevant:
            topic_memories_prompt = f"\nmemories specifically about {topic}:\n"
            for mem in relevant:
                topic_memories_prompt += f"  - {mem.text}\n"
    
    # Get tone guidelines (innocent drinks style)
    tone_prompt = get_tone_prompt(grade_level)
    
    # Get widget examples if specified
    examples_prompt = ""
    if widget_type:
        try:
            retriever = ExampleRetriever()
            examples_prompt = retriever.get_examples_for_prompt(widget_type=widget_type, num_examples=2)
        except Exception as e:
            print(f"[memory_personalizer] Example retrieval failed: {e}")
    
    full_prompt = f"""
{memory_prompt}
{topic_memories_prompt}

{tone_prompt}

{examples_prompt}

---
TASK:
{base_prompt}

remember: 
- make it personal - use their interests, pets, family names
- if they struggle with this topic, be extra gentle
- keep the innocent drinks tone - casual, friendly, lowercase
- like a nice friend who happens to know maths
"""
    
    return full_prompt


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Get personalization context for a user")
    parser.add_argument("user_id", help="User ID to get memories for")
    parser.add_argument("--prompt", "-p", help="Base prompt to personalize")
    
    args = parser.parse_args()
    
    personalizer = MemoryPersonalizer()
    
    if args.prompt:
        prompt = generate_personalized_question_prompt(args.user_id, args.prompt)
        print(prompt)
    else:
        prompt = personalizer.get_personalization_prompt(args.user_id)
        print(prompt)
