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

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if _GEMINI_API_KEY:
    try:
        from google import genai as genai_client  # google-genai
        genai_client = genai_client.Client(api_key=_GEMINI_API_KEY)
        GENAI_PROVIDER = "google-genai"
    except Exception:
        try:
            import google.generativeai as genai  # google-generativeai (legacy)
            genai.configure(api_key=_GEMINI_API_KEY)
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
        
        # Load tone guidelines (prefer shared tone_guidelines.py)
        self.tone_guidelines = None  # computed per-question by grade via content.tone_guidelines.get_tone_prompt()
        
        print(f"[QuestionGenerator] Connected to local MongoDB")
        print(f"[QuestionGenerator] Reference questions: {self.questions.count_documents({}):,}")
        print(f"[QuestionGenerator] Output dir: {QUESTIONS_DIR}")
    
    def _load_tone_guidelines(self) -> str:
        """Load Innocent Drinks tone guidelines (fallback if module import fails)."""
        return """
TONE GUIDELINES (innocent drinks style):

Write like innocent drinks - chatty, humble, a bit cheeky. Like a nice friend who happens to know the subject.

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

❌ "What is the main idea of this passage?"
✅ "what's this passage really about? sum it up in your own words."

❌ "Which state of matter is ice?"
✅ "ice. solid, liquid, or gas? (think about what happens when you touch it)"

CRITICAL: vary your openings! use different ones each time:
• "so here's the thing."
• "have a go at this."
• "here we go."
• "quick one."
• "try this."
• "ooh, this is good."
• just dive straight into the scenario (no opener)

🚫 BANNED PHRASES (never use):
• "right then" / "right," / "right, so"
• "okay this is a fun one" / "okay, try this one"
• "okay, let's..." / "let's dive in" / "let's see if"
• "alright, here's the thing" / "alright, so"
• "can you figure out" / "let's see if you can"
• "here's a head-scratcher" / "here's a fun one"
• "Great job!" / "Excellent!" / "Amazing!"

ENCOURAGEMENT TO ADD:
• "(no rush, we'll wait)"
• "(you've got this)"
• "(take your time)"
• "(we believe in you)"
"""

    def _get_subject_context(self, subject: str) -> str:
        """Get subject-specific context for question generation."""
        contexts = {
            "math": """
SUBJECT: MATH
Make numbers feel friendly. Use real-world scenarios kids can picture.
- use food, toys, animals, games as context
- if personalization available, use their interests/pets
- fractions? think pizza slices, cake pieces
- geometry? shapes are everywhere, point them out
""",
            "science": """
SUBJECT: SCIENCE  
Science is about curiosity. Frame questions as mini-discoveries.
- "what do you reckon happens when..."
- "here's something cool about..."
- make it feel like an experiment, not a test
- use everyday examples they can relate to
""",
            "reading": """
SUBJECT: READING
Reading comprehension should feel like a conversation about a story.
- "what's this passage really saying?"
- "if you had to explain this to a friend..."
- avoid formal literary analysis language
- focus on understanding, not memorizing
""",
            "computer_science": """
SUBJECT: CODING
Code is just giving instructions to a computer.
- think of it like writing a recipe
- break things into simple steps
- "what happens if we..."
- make debugging feel like solving a puzzle
""",
        }
        return contexts.get(subject, contexts["math"])

    def _validate_question_structure(self, question: Dict, expected_widget_type: str) -> None:
        """
        Validate the generated question has proper widget data.

        Raises ValueError if validation fails - this allows retry logic to
        regenerate the question.
        """
        widgets = question.get("widgets", {})

        if not widgets:
            raise ValueError("Generated question has no widgets")

        for widget_id, widget in widgets.items():
            if not isinstance(widget, dict):
                raise ValueError(f"Widget '{widget_id}' is not a dict: {type(widget)}")

            wtype = widget.get("type")
            if not wtype:
                raise ValueError(f"Widget '{widget_id}' has no type")

            options = widget.get("options", {})

            if wtype == "radio":
                choices = options.get("choices", [])
                if not isinstance(choices, list):
                    raise ValueError(f"Radio widget '{widget_id}' choices is not a list")
                if len(choices) < 2:
                    raise ValueError(
                        f"Radio widget '{widget_id}' has {len(choices)} choices, need at least 2"
                    )
                # Validate each choice has content
                for i, choice in enumerate(choices):
                    if not isinstance(choice, dict):
                        raise ValueError(f"Choice {i} in widget '{widget_id}' is not a dict")
                    if not choice.get("content"):
                        raise ValueError(f"Choice {i} in widget '{widget_id}' has no content")
                # Ensure at least one correct answer
                has_correct = any(c.get("correct") for c in choices)
                if not has_correct:
                    raise ValueError(f"Radio widget '{widget_id}' has no correct answer marked")

            elif wtype == "numeric-input":
                answers = options.get("answers", [])
                if not answers:
                    raise ValueError(f"Numeric input '{widget_id}' has no answers")

            elif wtype == "dropdown":
                choices = options.get("choices", [])
                if not isinstance(choices, list) or len(choices) < 2:
                    raise ValueError(
                        f"Dropdown widget '{widget_id}' needs at least 2 choices"
                    )

            elif wtype == "orderer":
                correct_options = options.get("correctOptions", [])
                if not correct_options:
                    raise ValueError(f"Orderer widget '{widget_id}' has no correctOptions")

        print(f"  [VALIDATION] Question structure valid: {len(widgets)} widget(s)")
    
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
    
    # Hardcoded fallback schemas in case DB lookup fails
    FALLBACK_WIDGET_SCHEMAS = {
        "radio": {
            "widget_name": "radio 1",
            "type": "radio",
            "options": {
                "choices": [
                    {"content": "Choice A text here", "correct": False},
                    {"content": "Choice B text here", "correct": False},
                    {"content": "Choice C text here", "correct": True},
                    {"content": "Choice D text here", "correct": False}
                ],
                "randomize": False,
                "multipleSelect": False
            }
        },
        "numeric-input": {
            "widget_name": "numeric-input 1",
            "type": "numeric-input",
            "options": {
                "value": 42,
                "correctAnswer": "42",
                "answerFormat": "integer"
            }
        },
        "dropdown": {
            "widget_name": "dropdown 1",
            "type": "dropdown",
            "options": {
                "choices": [
                    {"content": "Option A", "correct": False},
                    {"content": "Option B", "correct": True},
                    {"content": "Option C", "correct": False}
                ]
            }
        },
        "orderer": {
            "widget_name": "orderer 1",
            "type": "orderer",
            "options": {
                "correctOptions": ["First", "Second", "Third"],
                "otherOptions": []
            }
        }
    }

    def get_widget_schema(self, widget_type: str) -> Dict:
        """Get widget schema from a real example, with fallback to hardcoded schemas."""
        # Try DB first
        example = self.questions.find_one({"widget_types": widget_type})
        if example:
            question = example.get("question", {})
            widgets = question.get("widgets", {})

            for widget_name, widget_config in widgets.items():
                if widget_config.get("type") == widget_type:
                    return {
                        "widget_name": widget_name,
                        "type": widget_type,
                        "options": widget_config.get("options", {})
                    }

        # Fallback to hardcoded schema
        if widget_type in self.FALLBACK_WIDGET_SCHEMAS:
            print(f"  [WARNING] Using fallback schema for {widget_type} (DB lookup failed)")
            return self.FALLBACK_WIDGET_SCHEMAS[widget_type]

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
        
        # Build avoid openers prompt - show first 3-4 words of each used opener
        avoid_prompt = ""
        if used_openers:
            avoid_prompt = f"""
🚨 CRITICAL - ALREADY USED OPENERS (you MUST use a COMPLETELY different opening structure):
{chr(10).join(f'- "{o}"' for o in used_openers[-8:])}

DO NOT start your question with any variation of the above phrases.
Try: starting directly with the scenario, using "so", "here we go", "quick one", or no opener at all."""
        
        # Build user memories prompt
        memories_prompt = ""
        if user_memories:
            memories_prompt = f"\nUSER MEMORIES (personalize with these):\n{user_memories}"
        
        # Tone prompt - use the authoritative tone_guidelines module
        from content.tone_guidelines import get_tone_prompt
        tone_prompt = get_tone_prompt(grade)
        
        # Get subject-specific context
        subject_context = self._get_subject_context(subject)

        # Main prompt
        prompt = f"""
{tone_prompt}
{subject_context}
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

🚨 CRITICAL TONE RULES (the server validates output and REJECTS violations):

BANNED OPENERS (these WILL fail validation - never use):
• "right," / "right, so" / "right so" / "right, let's" / "right then"
• "okay," / "okay, so" / "okay so" / "okay, let's" / "okay let's" 
• "okay, here's" / "okay here's the thing" / "okay, check" / "okay check"
• "okay this one" / "okay this one's" / "okay this is a fun one"
• "alright," / "alright, so" / "alright so" / "alright, let's"
• "alright, here's" / "alright here's the thing"

BANNED PATTERNS:
• "let's dive in" / "let's get started" / "let's see if" / "let's try"
• "can you figure out" / "here's a head-scratcher" / "here's a fun one"
• "Great job!" / "Excellent!" / "Amazing!" (too hype-y)

✅ SAFE OPENERS (use these, or skip opener entirely):
• "so" (alone, not "okay so")
• "here we go." / "have a go at this." / "try this." / "quick one."
• or just start directly with the scenario (no opener)

Keep it warm and casual. Encouragement: "(you've got this)" or "(no rush)" - gentle, not hype.

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
        # - attempt 0: normal generation
        # - attempt 1-2: tone-corrected retries if validation fails
        tone_corrections: str = ""
        for attempt in range(3):
            try:
                attempt_prompt = prompt
                if tone_corrections:
                    attempt_prompt = f"{prompt}\n\n---\n\nTONE FIX NEEDED (you broke the rules last time):\n{tone_corrections}\n\nRewrite the output so it passes validation. Return ONLY JSON." 

                if self.genai_provider == "google-genai":
                    response = self.genai_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=attempt_prompt
                    )
                    text = (getattr(response, "text", None) or "").strip()
                    if not text:
                        text = str(response)
                else:
                    response = self.genai_model.generate_content(attempt_prompt)
                    text = response.text.strip()
                
                # Clean up response
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()
                
                # Parse JSON
                data = json.loads(text)

                # Tone validation (content itself, not wrapper text)
                # Import with explicit error handling - DO NOT skip validation
                from content.tone_guidelines import validate_tone
                
                content_text = str(data.get("content", ""))
                violations: List[str] = list(validate_tone(content_text))
                
                for h in (data.get("hints") or []):
                    if isinstance(h, dict):
                        violations.extend(validate_tone(str(h.get("content", ""))))

                violations = sorted(set(v for v in violations if v))
                
                if violations:
                    tone_corrections = "\n".join(f"- {v}" for v in violations)
                    print(f"  [TONE_VALIDATION] FAILED (attempt {attempt+1}/3): {content_text[:80]}...")
                    print(f"    Violations: {tone_corrections}")
                    if attempt < 2:
                        # Feed back into the next attempt.
                        time.sleep(0.5)
                        continue
                    # Last attempt: hard fail so caller can retry at a higher level.
                    raise ValueError(f"Tone validation failed: {tone_corrections}")
                else:
                    print(f"  [TONE_VALIDATION] PASSED (attempt {attempt+1}/3): {content_text[:60]}...")

                # Generate unique ID
                question_id = f"gen_{grade}_{subject}_{topic.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
                
                # Extract widget types
                widgets = data.get("widgets", {})
                widget_types_list = [w.get("type") for w in widgets.values() if isinstance(w, dict)]
                
                # Validate question structure before returning
                self._validate_question_structure(data, widget_type)

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
                
                # Track opener - extract first 3-4 words for more robust comparison
                # This catches "alright, here's the thing." vs "alright, here's the thing, leo."
                content = question.question.get("content", "").lower().strip()
                words = content.split()[:4]  # First 4 words
                opener_pattern = " ".join(words)
                used_openers.append(opener_pattern)
                
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
