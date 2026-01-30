#!/usr/bin/env python3
"""
Question Generator Module

Generates personalized questions using:
- Local MongoDB (questions_unified) as reference examples
- Gemini API for generation
- Innocent Drinks tone guidelines
- User memory personalization

Output: 
- Questions in finalized Perseus schema
- Stored in: questions/generated questions/{grade}/{subject}/
"""

import json
import os
import sys
import time
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables early (needed for GEMINI_API_KEY)
load_dotenv()

# Gemini client selection (google-genai preferred)
GENAI_PROVIDER = None
genai_client = None
genai_model = None

try:
    from google import genai as genai_client  # google-genai
    genai_client = genai_client.Client(api_key=os.getenv('GEMINI_API_KEY', ''))
    GENAI_PROVIDER = "google-genai"
except Exception:
    try:
        import google.generativeai as genai  # google-generativeai (legacy)
        genai.configure(api_key=os.getenv('GEMINI_API_KEY', ''))
        genai_model = genai.GenerativeModel('gemini-2.0-flash')
        GENAI_PROVIDER = "google-generativeai"
    except Exception:
        GENAI_PROVIDER = None

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
QUESTIONS_DIR = PROJECT_ROOT / "questions" / "generated questions"


@dataclass
class GeneratedQuestion:
    """A generated question in finalized schema."""
    question_id: str
    question: Dict[str, Any]
    hints: List[Dict[str, Any]]
    answer_area: Dict[str, Any]
    widget_types: List[str]
    grade: str
    subject: str
    topic: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "question_id": self.question_id,
            "question": self.question,
            "hints": self.hints,
            "answer_area": self.answer_area,
            "widget_types": self.widget_types,
            "grade": self.grade,
            "subject": self.subject,
            "topic": self.topic,
            "metadata": self.metadata
        }


class QuestionGenerator:
    """
    Generates personalized questions using Gemini + reference examples.
    
    Stores questions in: questions/generated questions/{grade}/{subject}/
    """
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize with local MongoDB connection."""
        self.client = MongoClient(mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
        self.db = self.client["ai_tutor"]
        self.questions = self.db["questions_unified"]
        
        # Gemini model
        if GENAI_PROVIDER is None:
            raise RuntimeError("Gemini client not available. Install google-genai or google-generativeai and set GEMINI_API_KEY.")
        self.genai_provider = GENAI_PROVIDER
        self.genai_client = genai_client
        self.genai_model = genai_model
        
        # Ensure output directories exist
        QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load tone guidelines
        self.tone_guidelines = self._load_tone_guidelines()
        
        print(f"[QuestionGenerator] Connected to local MongoDB")
        print(f"[QuestionGenerator] Reference questions: {self.questions.count_documents({}):,}")
        print(f"[QuestionGenerator] Output dir: {QUESTIONS_DIR}")
    
    def _load_tone_guidelines(self) -> str:
        """Load Innocent Drinks tone guidelines."""
        return """
TONE GUIDELINES (innocent drinks style):

Write like innocent drinks - chatty, humble, a bit cheeky. Like a nice friend who happens to know maths.

WRITING STYLE:
• lowercase where possible, casual punctuation
• short sentences. like this. easy peasy.
• slightly self-aware and playful
• no corporate speak, no trying too hard
• gentle humour, never mean
• talk like a real person, not a textbook

EXAMPLE REWRITES:
❌ "Count the objects. How many are there?"
✅ "so there are some apples here. have a count. how many did you get?"

❌ "What is 3 + 2?"
✅ "you've got 3 apples. someone nice gives you 2 more. how many now? (we believe in you)"

❌ "Select the correct answer."
✅ "pick the one you reckon is right. no pressure."

CRITICAL: vary your openings! use different ones each time:
• "so here's the thing."
• "have a go at this."
• "here we go."
• "this one's interesting."
• "quick one."
• "try this."
• "alright."
• "ooh, this is good."
• "here's a puzzle."
• just dive straight into the scenario (no opener)

BANNED PHRASES (never use):
• "right then"
• "right,"  
• "okay this is a fun one"
• "okay, try this one"

ENCOURAGEMENT TO ADD:
• "(no rush, we'll wait)"
• "(you've got this)"
• "(take your time)"
"""
    
    def get_reference_examples(
        self,
        widget_type: str,
        num_examples: int = 2
    ) -> List[Dict]:
        """Get reference examples from questions_unified for a widget type."""
        examples = list(self.questions.find(
            {"widget_types": widget_type},
            {"question": 1, "hints": 1, "answer_area": 1, "widget_types": 1}
        ).limit(num_examples))
        
        return examples
    
    def get_widget_schema(self, widget_type: str) -> Dict:
        """Get widget schema from a real example."""
        example = self.questions.find_one({"widget_types": widget_type})
        if not example:
            return {}
        
        question = example.get("question", {})
        widgets = question.get("widgets", {})
        
        for widget_name, widget_config in widgets.items():
            if widget_config.get("type") == widget_type:
                return {
                    "widget_name": widget_name,
                    "type": widget_type,
                    "options": widget_config.get("options", {})
                }
        
        return {}
    
    def generate_question(
        self,
        topic: str,
        widget_type: str,
        grade: str = "K-2",
        subject: str = "math",
        user_memories: Optional[str] = None,
        used_openers: Optional[List[str]] = None
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a single question.
        
        Args:
            topic: Topic (addition, fractions, etc.)
            widget_type: Widget type (radio, numeric-input, etc.)
            grade: K-2, 3-5, 6-8, 9-12
            subject: math, science, etc.
            user_memories: Optional personalization context
            used_openers: List of already-used openings to avoid
        
        Returns:
            GeneratedQuestion in finalized schema
        """
        # Get reference examples
        examples = self.get_reference_examples(widget_type, num_examples=2)
        widget_schema = self.get_widget_schema(widget_type)
        
        # Build examples prompt
        examples_prompt = ""
        if examples:
            examples_prompt = "REFERENCE EXAMPLES FROM DATABASE:\n"
            for i, ex in enumerate(examples, 1):
                q = ex.get("question", {})
                examples_prompt += f"\nExample {i}:\n"
                examples_prompt += f"Content: {q.get('content', '')[:200]}...\n"
                examples_prompt += f"Widgets: {json.dumps(list(q.get('widgets', {}).keys()))}\n"
        
        # Build avoid openers prompt
        avoid_prompt = ""
        if used_openers:
            avoid_prompt = f"\nALREADY USED OPENERS (use completely different ones):\n" + "\n".join(f"- {o}" for o in used_openers[-5:])
        
        # Build user memories prompt
        memories_prompt = ""
        if user_memories:
            memories_prompt = f"\nUSER MEMORIES (personalize with these):\n{user_memories}"
        
        # Main prompt
        prompt = f"""
{self.tone_guidelines}
{memories_prompt}
{avoid_prompt}

{examples_prompt}

WIDGET TYPE: {widget_type}
WIDGET SCHEMA: {json.dumps(widget_schema, indent=2)}

---

TASK: Generate a {grade} level {subject} question about {topic} using the {widget_type} widget.

Requirements:
1. Use the innocent drinks tone (chatty, lowercase, friendly)
2. Personalize with user memories if provided (pets, interests, family)
3. Follow the exact widget schema from examples
4. Include 2-3 helpful hints in the same friendly tone
5. Ensure the answer is correct and clear
6. Use a UNIQUE opening - not one from the "already used" list

Return ONLY valid JSON in this exact format:
{{
    "content": "the question text with widget placeholder [[☃ {widget_type} 1]]",
    "widgets": {{
        "{widget_type} 1": {{
            "type": "{widget_type}",
            "options": {{ ... correct widget options with answer ... }}
        }}
    }},
    "hints": [
        {{"content": "friendly hint 1", "widgets": {{}}}},
        {{"content": "friendly hint 2", "widgets": {{}}}}
    ],
    "answer_area": {{}}
}}

Return ONLY the JSON, no markdown code blocks.
"""
        
        # Generate with retry
        for attempt in range(3):
            try:
                if self.genai_provider == "google-genai":
                    response = self.genai_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    text = (getattr(response, "text", None) or "").strip()
                    if not text:
                        text = str(response)
                else:
                    response = self.genai_model.generate_content(prompt)
                    text = response.text.strip()
                
                # Clean up response
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()
                
                # Parse JSON
                data = json.loads(text)
                
                # Generate unique ID
                question_id = f"gen_{grade}_{subject}_{topic.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
                
                # Extract widget types
                widgets = data.get("widgets", {})
                widget_types_list = [w.get("type") for w in widgets.values() if isinstance(w, dict)]
                
                return GeneratedQuestion(
                    question_id=question_id,
                    question={
                        "content": data.get("content", ""),
                        "widgets": widgets,
                        "images": {}
                    },
                    hints=data.get("hints", []),
                    answer_area=data.get("answer_area", {}),
                    widget_types=widget_types_list,
                    grade=grade,
                    subject=subject,
                    topic=topic,
                    metadata={
                        "widget_type": widget_type,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "generator": "QuestionGenerator",
                        "model": "gemini-2.0-flash",
                        "personalized": user_memories is not None
                    }
                )
                
            except json.JSONDecodeError as e:
                print(f"  JSON parse error (attempt {attempt+1}): {e}")
                time.sleep(1)
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    wait = (attempt + 1) * 5
                    print(f"  Rate limited, waiting {wait}s...", flush=True)
                    time.sleep(wait)
                else:
                    print(f"  Error (attempt {attempt+1}): {e}")
                    time.sleep(1)
        
        return None
    
    def generate_batch(
        self,
        specifications: List[Dict],
        user_memories: Optional[str] = None,
        save_to_disk: bool = True
    ) -> List[GeneratedQuestion]:
        """
        Generate a batch of questions.
        
        Args:
            specifications: List of {"topic", "widget_type", "grade", "subject"}
            user_memories: Optional personalization context
            save_to_disk: Whether to save each question to disk
        
        Returns:
            List of GeneratedQuestion objects
        """
        questions = []
        used_openers = []
        
        for i, spec in enumerate(specifications):
            topic = spec["topic"]
            widget_type = spec["widget_type"]
            grade = spec.get("grade", "K-2")
            subject = spec.get("subject", "math")
            
            print(f"[{i+1}/{len(specifications)}] Generating {topic} ({widget_type}) for {grade} {subject}...", flush=True)
            
            question = self.generate_question(
                topic=topic,
                widget_type=widget_type,
                grade=grade,
                subject=subject,
                user_memories=user_memories,
                used_openers=used_openers
            )
            
            if question:
                questions.append(question)
                
                # Track opener
                opener = question.question.get("content", "")[:30].lower()
                used_openers.append(opener)
                
                # Save to disk
                if save_to_disk:
                    self.save_question(question)
                
                print(f"  ✓ {question.question.get('content', '')[:50]}...")
            else:
                print(f"  ✗ Failed")
            
            # Rate limit protection
            time.sleep(2)
        
        return questions
    
    def save_question(self, question: GeneratedQuestion) -> str:
        """
        Save a question to the folder structure.
        
        Structure: questions/generated questions/{grade}/{subject}/{question_id}.json
        
        Returns:
            Path to saved file
        """
        # Create directory structure
        grade_dir = QUESTIONS_DIR / question.grade
        subject_dir = grade_dir / question.subject
        subject_dir.mkdir(parents=True, exist_ok=True)
        
        # Save question file
        filepath = subject_dir / f"{question.question_id}.json"
        with open(filepath, "w") as f:
            json.dump(question.to_dict(), f, indent=2)
        
        # Update index.json for this subject
        self._update_index(subject_dir)
        
        return str(filepath)
    
    def _update_index(self, subject_dir: Path):
        """Update index.json listing all questions in a subject folder."""
        questions = []
        
        for filepath in subject_dir.glob("*.json"):
            if filepath.name == "index.json":
                continue
            
            try:
                with open(filepath) as f:
                    q = json.load(f)
                    questions.append({
                        "question_id": q.get("question_id"),
                        "topic": q.get("topic"),
                        "widget_types": q.get("widget_types", []),
                        "file": filepath.name
                    })
            except Exception as e:
                print(f"  Warning: Could not read {filepath}: {e}")
        
        # Write index
        index_path = subject_dir / "index.json"
        with open(index_path, "w") as f:
            json.dump({
                "count": len(questions),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "questions": questions
            }, f, indent=2)
    
    def save_to_mongodb(self, questions: List[GeneratedQuestion], collection_name: str = "generated_questions"):
        """Save generated questions to MongoDB."""
        collection = self.db[collection_name]
        
        docs = [q.to_dict() for q in questions]
        for doc in docs:
            doc["created_at"] = datetime.now(timezone.utc)
        
        if docs:
            result = collection.insert_many(docs)
            print(f"✓ Saved {len(result.inserted_ids)} questions to MongoDB ({collection_name})")
            return result.inserted_ids
        
        return []
    
    def get_folder_structure(self) -> Dict:
        """Get the current folder structure with question counts."""
        structure = {}
        
        for grade_dir in QUESTIONS_DIR.iterdir():
            if not grade_dir.is_dir():
                continue
            
            grade = grade_dir.name
            structure[grade] = {}
            
            for subject_dir in grade_dir.iterdir():
                if not subject_dir.is_dir():
                    continue
                
                subject = subject_dir.name
                
                # Count questions (excluding index.json)
                count = len([f for f in subject_dir.glob("*.json") if f.name != "index.json"])
                structure[grade][subject] = count
        
        return structure


# Default user memories for demo
DEFAULT_USER_MEMORIES = """
interests/likes:
  - loves dinosaurs, especially T-Rex
  - really into space and planets
  - plays minecraft all the time
  - enjoys baking cookies with mom

pets:
  - has a golden retriever called Buddy
  - recently got a hamster named Nugget

family:
  - younger sister called Emma (she's 5)
  - grandma makes the best pancakes

things they find tricky (be extra gentle here):
  - sometimes confused by word problems
  - fractions are hard

things they're good at:
  - really quick with addition
  - great at spotting patterns
"""


def main():
    """Generate questions and save to folder structure."""
    print("=" * 60)
    print("QUESTION GENERATOR")
    print("=" * 60)
    
    generator = QuestionGenerator()
    
    # Question specifications with grade and subject
    specs = [
        # K-2 Math
        {"topic": "addition", "widget_type": "numeric-input", "grade": "K-2", "subject": "math"},
        {"topic": "counting", "widget_type": "radio", "grade": "K-2", "subject": "math"},
        {"topic": "subtraction", "widget_type": "numeric-input", "grade": "K-2", "subject": "math"},
        {"topic": "shapes", "widget_type": "radio", "grade": "K-2", "subject": "math"},
        {"topic": "patterns", "widget_type": "orderer", "grade": "K-2", "subject": "math"},
        
        # 3-5 Math
        {"topic": "multiplication", "widget_type": "radio", "grade": "3-5", "subject": "math"},
        {"topic": "fractions", "widget_type": "dropdown", "grade": "3-5", "subject": "math"},
        {"topic": "division", "widget_type": "numeric-input", "grade": "3-5", "subject": "math"},
        {"topic": "word problems", "widget_type": "radio", "grade": "3-5", "subject": "math"},
        {"topic": "decimals", "widget_type": "input-number", "grade": "3-5", "subject": "math"},
    ]
    
    print(f"\nGenerating {len(specs)} questions with personalization...")
    print(f"Output: {QUESTIONS_DIR}\n")
    
    questions = generator.generate_batch(specs, user_memories=DEFAULT_USER_MEMORIES)
    
    print(f"\n{'=' * 60}")
    print(f"✓ Generated {len(questions)} questions")
    print(f"{'=' * 60}")
    
    # Show folder structure
    print("\nFolder structure:")
    structure = generator.get_folder_structure()
    for grade, subjects in sorted(structure.items()):
        print(f"  {grade}/")
        for subject, count in sorted(subjects.items()):
            print(f"    {subject}/: {count} questions")
    
    # Also save to MongoDB
    generator.save_to_mongodb(questions)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
