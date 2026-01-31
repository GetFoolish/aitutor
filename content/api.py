#!/usr/bin/env python3
"""
Generated Questions API

Serves generated questions in the same format as DASH API,
so the frontend can use them interchangeably.

Endpoints:
- GET /api/generated/questions/{count} - Get generated questions
- GET /api/generated/questions/grade/{grade}/{count} - Get by grade
- GET /api/generated/list - List all available questions
"""

import os
import sys
import json
import time
import hashlib
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables (supports running without run_tutor.sh)
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
QUESTIONS_DIR = PROJECT_ROOT / "questions" / "generated questions"

app = FastAPI(title="Generated Questions API", version="1.0.0")

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection (local by default, override with MONGODB_URI)
mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(mongodb_uri)
db = client["ai_tutor"]
generated_questions = db["generated_questions"]

# Import ExampleRetriever for few-shot learning
try:
    sys.path.append(str(Path(__file__).parent))
    from example_retriever import ExampleRetriever
    example_retriever = ExampleRetriever()
    print("[ContentAPI] ✅ ExampleRetriever initialized with questions_unified")
except Exception as e:
    print(f"[ContentAPI] ⚠️ ExampleRetriever not available: {e}")
    example_retriever = None


def generate_sha256(content: str) -> str:
    """Generate SHA256 hash for content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_ka_id() -> str:
    """Generate Khan Academy style ID (x + 16 hex chars)"""
    return 'x' + uuid.uuid4().hex[:16]


def infer_problem_type(question_content: str, widgets: dict) -> str:
    """Infer problem type from question content and widgets"""
    content_lower = question_content.lower()
    widget_types = list(widgets.keys())

    # Math operations
    if any(word in content_lower for word in ['add', 'plus', 'sum', 'total', 'altogether']):
        return 'Add or subtract'
    elif any(word in content_lower for word in ['subtract', 'minus', 'difference', 'take away']):
        return 'Add or subtract'
    elif any(word in content_lower for word in ['multiply', 'times', 'product']):
        return 'Multiply or divide'
    elif any(word in content_lower for word in ['divide', 'split', 'share']):
        return 'Multiply or divide'
    elif any(word in content_lower for word in ['fraction', 'half', 'third', 'quarter']):
        return 'Fractions'

    # General types
    elif 'radio' in str(widget_types):
        return 'Multiple choice'
    elif 'numeric-input' in str(widget_types):
        return 'Numeric answer'
    else:
        return 'General question'


def requires_screen_or_mouse(widgets: dict) -> bool:
    """Determine if question requires screen/mouse (has images, interactive widgets)"""
    for widget_config in widgets.values():
        widget_type = widget_config.get('type', '')
        if widget_type in ['image', 'interactive-graph', 'plotter', 'grapher']:
            return True
        # Check if widget has images
        if widget_config.get('options', {}).get('backgroundImage'):
            return True
    return False


def fix_numeric_input_widgets(widgets: dict) -> dict:
    """
    Fix numeric-input widgets for proper Perseus scoring.

    Issues fixed:
    - Remove 'simplify: required' which causes string/number comparison failures
    - Ensure 'strict: false' for more forgiving input matching
    - Add 'graded: true' required by Perseus scorer
    """
    for widget_name, widget_config in widgets.items():
        # Add required widget-level properties
        widget_config["graded"] = True
        widget_config["static"] = False

        if widget_config.get("type") == "numeric-input":
            options = widget_config.get("options", {})
            answers = options.get("answers", [])
            for answer in answers:
                # Remove 'simplify' - causes issues with string "4" vs number 4
                answer.pop("simplify", None)
                # Ensure forgiving comparison
                answer["strict"] = False
                # Add maxError if not present
                if "maxError" not in answer:
                    answer["maxError"] = None
                if "message" not in answer:
                    answer["message"] = ""
    return widgets


def fix_radio_widgets(widgets: dict) -> dict:
    """
    Fix radio widgets for proper Perseus rendering.

    The AI sometimes generates radio widgets in wrong format:
    - Wrong: {"options": {"3": false, "4": true, "5": false}}
    - Correct: {"options": {"choices": [{"content": "3", "correct": false}, ...]}}

    This function converts the wrong format to the correct Perseus format.
    """
    for widget_name, widget_config in widgets.items():
        if widget_config.get("type") == "radio":
            options = widget_config.get("options", {})

            # Check if choices already exists and is properly formatted
            if "choices" in options and isinstance(options["choices"], list):
                # Already correct format - just ensure each choice has required fields
                for choice in options["choices"]:
                    if isinstance(choice, dict):
                        if "content" not in choice:
                            choice["content"] = ""
                        if "correct" not in choice:
                            choice["correct"] = False
                continue

            # Check for wrong format: options like {"3": false, "4": true}
            # These are key-value pairs where keys are answer text and values are booleans
            wrong_format_choices = {}
            for key, value in list(options.items()):
                # Skip known Perseus option keys
                if key in ["choices", "randomize", "multipleSelect", "countChoices",
                          "deselectEnabled", "displayCount", "noneOfTheAbove"]:
                    continue
                # If value is boolean, this is likely wrong format
                if isinstance(value, bool):
                    wrong_format_choices[key] = value

            # Convert wrong format to correct format
            if wrong_format_choices:
                choices = []
                for answer_text, is_correct in wrong_format_choices.items():
                    choices.append({
                        "content": str(answer_text),
                        "correct": bool(is_correct)
                    })

                # Remove the wrong keys from options
                for key in wrong_format_choices.keys():
                    options.pop(key, None)

                # Add proper choices array
                options["choices"] = choices
                options["randomize"] = options.get("randomize", True)

                print(f"[FIX_RADIO] Converted {widget_name}: {len(choices)} choices")

            # Ensure at least one choice exists
            if not options.get("choices"):
                print(f"[FIX_RADIO] WARNING: {widget_name} has no choices!")

    return widgets


class PerseusQuestion(BaseModel):
    """Perseus-compatible question format."""
    question: dict
    answerArea: dict
    hints: list
    itemDataVersion: Optional[dict] = None
    dash_metadata: Optional[dict] = None


@app.get("/health")
def health():
    """Health check."""
    count = generated_questions.count_documents({})
    return {
        "status": "ready",
        "generated_questions": count,
        "questions_dir": str(QUESTIONS_DIR)
    }

@app.get("/test-new-endpoint")
def test_new_endpoint():
    """Test endpoint to verify server is using latest code."""
    return {"message": "SUCCESS - This endpoint was added on Jan 30, 2026", "version": "2.0"}


@app.get("/api/generated/questions/{count}", response_model=List[PerseusQuestion])
def get_generated_questions(count: int, grade: Optional[str] = None, subject: str = "math"):
    """
    Get generated questions in Perseus format (same as DASH API).
    
    Args:
        count: Number of questions to return
        grade: Optional grade filter (K-2, 3-5, 6-8, 9-12)
        subject: Subject filter (default: math)
    """
    # Only get questions that have valid widgets (can be answered)
    query = {
        "subject": subject,
        "question.widgets": {"$exists": True, "$ne": {}}
    }
    if grade:
        query["grade"] = grade
    
    # Get questions from MongoDB
    questions = list(generated_questions.find(query).limit(count))
    
    if not questions:
        # Fallback: try loading from files
        questions = load_questions_from_files(grade, subject, count)
    
    if not questions:
        raise HTTPException(status_code=404, detail="No generated questions found")
    
    # Convert to Perseus format
    perseus_items = []
    for q in questions:
        question_data = q.get("question", {})
        content = question_data.get("content", "")
        widgets = question_data.get("widgets", {})
        
        # FIX: Clean up widgets for proper scoring/rendering
        widgets = fix_numeric_input_widgets(widgets)
        widgets = fix_radio_widgets(widgets)

        # FIX: Ensure content has widget placeholders
        # If content doesn't have [[☃ widget-name]], append them
        for widget_name in widgets.keys():
            placeholder = f"[[☃ {widget_name}]]"
            if placeholder not in content:
                # Append widget placeholder to content
                content = content.rstrip() + f" {placeholder}"
        
        # Update question data with fixed content
        question_data["content"] = content
        question_data["widgets"] = widgets
        
        perseus_items.append({
            "question": question_data,
            "answerArea": q.get("answer_area", {}),
            "hints": q.get("hints", []),
            "itemDataVersion": {"major": 0, "minor": 1},
            "dash_metadata": {
                "dash_question_id": q.get("question_id"),
                "skill_ids": [f"gen_{q.get('topic', 'unknown')}"],
                "difficulty": 0.5,
                "expected_time_seconds": 60,
                "slug": q.get("question_id"),
                "skill_names": [q.get("topic", "Generated")],
                "grade": q.get("grade"),
                "subject": q.get("subject"),
                "topic": q.get("topic"),
                "source": "generated"
            }
        })
    
    return perseus_items


@app.get("/api/generated/questions/grade/{grade}/{count}", response_model=List[PerseusQuestion])
def get_questions_by_grade(grade: str, count: int, subject: str = "math"):
    """Get generated questions for a specific grade."""
    return get_generated_questions(count, grade=grade, subject=subject)


@app.get("/api/generated/list")
def list_generated_questions():
    """List all available generated questions grouped by grade/subject."""
    result = {}
    
    # From MongoDB
    pipeline = [
        {"$group": {
            "_id": {"grade": "$grade", "subject": "$subject"},
            "count": {"$sum": 1},
            "topics": {"$addToSet": "$topic"}
        }},
        {"$sort": {"_id.grade": 1, "_id.subject": 1}}
    ]
    
    for doc in generated_questions.aggregate(pipeline):
        grade = doc["_id"].get("grade") or "unknown"
        subject = doc["_id"].get("subject") or "math"
        
        if grade not in result:
            result[grade] = {}
        
        result[grade][subject] = {
            "count": doc["count"],
            "topics": [t for t in doc.get("topics", []) if t]  # Filter out None
        }
    
    # Also check file system
    for grade_dir in QUESTIONS_DIR.iterdir():
        if not grade_dir.is_dir():
            continue
        grade = grade_dir.name
        if grade not in result:
            result[grade] = {}
        
        for subject_dir in grade_dir.iterdir():
            if not subject_dir.is_dir():
                continue
            subject = subject_dir.name
            
            # Count files
            count = len([f for f in subject_dir.glob("*.json") if f.name != "index.json"])
            
            if subject not in result[grade]:
                result[grade][subject] = {"count": count, "topics": [], "source": "files"}
    
    return {
        "grades": result,
        "total": generated_questions.count_documents({})
    }


def load_questions_from_files(grade: Optional[str], subject: str, count: int) -> List[dict]:
    """Load questions from file system as fallback."""
    import json
    
    questions = []
    
    if grade:
        grade_dirs = [QUESTIONS_DIR / grade]
    else:
        grade_dirs = [d for d in QUESTIONS_DIR.iterdir() if d.is_dir()]
    
    for grade_dir in grade_dirs:
        if not grade_dir.exists():
            continue
        
        subject_dir = grade_dir / subject
        if not subject_dir.exists():
            continue
        
        for qfile in subject_dir.glob("*.json"):
            if qfile.name == "index.json":
                continue
            
            try:
                with open(qfile) as f:
                    q = json.load(f)
                    questions.append(q)
                    
                    if len(questions) >= count:
                        return questions
            except Exception as e:
                print(f"Error loading {qfile}: {e}")
    
    return questions


# ============================================================
# Additional API Endpoints
# ============================================================

@app.get("/api/topics")
def get_topics():
    """Get all available topics grouped by grade."""
    pipeline = [
        {"$group": {
            "_id": {"grade": "$grade", "topic": "$topic"},
            "count": {"$sum": 1}
        }},
        {"$group": {
            "_id": "$_id.grade",
            "topics": {"$push": {"name": "$_id.topic", "count": "$count"}}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    result = []
    for doc in generated_questions.aggregate(pipeline):
        result.append({
            "grade": doc["_id"],
            "topics": doc["topics"]
        })
    
    return {"grades": result, "total_topics": sum(len(g["topics"]) for g in result)}


@app.get("/api/skills")
def get_skills(limit: int = 50, grade: Optional[str] = None):
    """Get available skills/topics."""
    query = {}
    if grade:
        query["grade"] = grade
    
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$topic",
            "count": {"$sum": 1},
            "grades": {"$addToSet": "$grade"},
            "sample_id": {"$first": "$question_id"}
        }},
        {"$limit": limit},
        {"$sort": {"count": -1}}
    ]
    
    skills = []
    for doc in generated_questions.aggregate(pipeline):
        skills.append({
            "skill": doc["_id"],
            "count": doc["count"],
            "grades": doc["grades"],
            "sample_question_id": doc["sample_id"]
        })
    
    return {"skills": skills, "total": len(skills)}


class GenerateRequest(BaseModel):
    """Request to generate a new question."""
    skill: str
    grade_level: str = "K-2"
    difficulty: str = "easy"
    style: str = "innocent"  # innocent = Innocent Drinks style


@app.post("/api/generate/question")
async def generate_question_endpoint(request: GenerateRequest):
    """
    Generate a new question on-the-fly using the content generation system.
    
    This is slower than fetching pre-generated questions but allows
    for custom skill/grade combinations.
    """
    try:
        # Try to import the generator
        from content.question_generator import QuestionGenerator

        generator = QuestionGenerator()
        generated = generator.generate_question(
            topic=request.skill,
            widget_type="radio",
            grade=request.grade_level,
            subject="math"
        )

        if not generated:
            raise HTTPException(status_code=500, detail="Question generator returned no output")

        return {
            "question": generated.question,
            "answerArea": generated.answer_area,
            "hints": generated.hints,
            "dash_metadata": {
                "skill_ids": [f"gen_{request.skill}"],
                "grade": request.grade_level,
                "source": "generated_live"
            }
        }
    except ImportError:
        # Generator not available - return a sample from DB
        query = {"topic": {"$regex": request.skill, "$options": "i"}}
        if request.grade_level:
            query["grade"] = request.grade_level
        
        sample = generated_questions.find_one(query)
        if sample:
            return {
                "question": sample.get("question", {}),
                "answerArea": sample.get("answer_area", {}),
                "hints": sample.get("hints", []),
                "dash_metadata": {
                    "skill_ids": [f"gen_{sample.get('topic')}"],
                    "grade": sample.get("grade"),
                    "source": "generated_cached"
                }
            }
        
        raise HTTPException(status_code=501, detail="Question generator not available and no cached questions match")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats():
    """Get statistics about generated questions."""
    total = generated_questions.count_documents({})
    
    # By grade
    by_grade = list(generated_questions.aggregate([
        {"$group": {"_id": "$grade", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]))
    
    # By topic
    by_topic = list(generated_questions.aggregate([
        {"$group": {"_id": "$topic", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]))
    
    return {
        "total_questions": total,
        "by_grade": {d["_id"]: d["count"] for d in by_grade},
        "top_topics": {d["_id"]: d["count"] for d in by_topic}
    }


# MOVED TO END OF FILE: if __name__ == "__main__" block
# This ensures all endpoints are defined before uvicorn starts


# ============================================
# ON-THE-FLY ASSESSMENT GENERATION
# ============================================

from pydantic import BaseModel as PydanticBaseModel

class AssessmentRequest(PydanticBaseModel):
    grade: str
    topics: List[str]
    count: int = 10


@app.post("/api/generate/assessment")
def generate_assessment_on_the_fly(request: AssessmentRequest):
    """
    Generate assessment questions on the fly based on grade and topics.
    
    For now, pulls from existing questions filtered by grade/topics.
    In production, this would call the question generator in real-time.
    """
    # Build query for MongoDB
    query = {
        "question.widgets": {"$exists": True, "$ne": {}},
    }
    
    # Filter by grade
    if request.grade:
        query["grade"] = request.grade
    
    # Filter by topics if specified
    if request.topics:
        query["topic"] = {"$in": request.topics}
    
    # Get questions from MongoDB
    questions = list(generated_questions.find(query).limit(request.count))
    
    # If not enough questions with exact topics, get more from same grade
    if len(questions) < request.count:
        fallback_query = {
            "question.widgets": {"$exists": True, "$ne": {}},
            "grade": request.grade
        }
        additional = list(generated_questions.find(fallback_query).limit(request.count - len(questions)))
        questions.extend(additional)
    
    if not questions:
        return []
    
    # Convert to Perseus format
    perseus_items = []
    for q in questions:
        question_data = q.get("question", {})
        content = question_data.get("content", "")
        widgets = question_data.get("widgets", {})
        
        # FIX: Clean up widgets for proper scoring/rendering
        widgets = fix_numeric_input_widgets(widgets)
        widgets = fix_radio_widgets(widgets)

        # FIX: Ensure content has widget placeholders
        for widget_name in widgets.keys():
            placeholder = f"[[☃ {widget_name}]]"
            if placeholder not in content:
                content = content.rstrip() + f" {placeholder}"

        question_data["content"] = content
        question_data["widgets"] = widgets

        perseus_items.append({
            "question": question_data,
            "answerArea": q.get("answer_area", {}),
            "hints": q.get("hints", []),
            "itemDataVersion": {"major": 0, "minor": 1},
            "dash_metadata": {
                "dash_question_id": q.get("question_id"),
                "skill_ids": [f"gen_{q.get('topic', 'unknown')}"],
                "difficulty": 0.5,
                "expected_time_seconds": 60,
                "slug": q.get("question_id"),
                "skill_names": [q.get("topic", "Generated")],
                "grade": q.get("grade"),
                "subject": q.get("subject"),
                "topic": q.get("topic"),
                "source": "generated"
            }
        })

    return perseus_items


# ============================================
# LIVE QUESTION GENERATION (ON THE FLY)
# ============================================

GENAI_AVAILABLE = False
GENAI_PROVIDER = None
genai_client = None
genai_model = None

try:
    from google import genai as genai_client  # google-genai
    genai_client = genai_client.Client(api_key=os.getenv('GEMINI_API_KEY', ''))
    GENAI_AVAILABLE = True
    GENAI_PROVIDER = "google-genai"
except Exception:
    try:
        import google.generativeai as genai  # google-generativeai (legacy)
        genai.configure(api_key=os.getenv('GEMINI_API_KEY', ''))
        genai_model = genai.GenerativeModel('gemini-2.0-flash')
        GENAI_AVAILABLE = True
        GENAI_PROVIDER = "google-generativeai"
    except Exception:
        GENAI_AVAILABLE = False
        print("[WARNING] Gemini client not available. Live generation disabled.")

class LiveGenerationRequest(PydanticBaseModel):
    prompt: str  # Free text: what the user wants to learn
    grade: str   # K-2, 3-5, 6-8, 9-12
    subject: str = "math"  # math, english, science, etc.
    language: str = "en"  # Language code: en, es, fr, de, zh, hi, ar, pt, ja, ko
    count: int = 5
    force_new: bool = False  # Skip cache and generate fresh questions

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "hi": "Hindi",
    "ar": "Arabic",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
}

# Widget types to rotate through for variety
WIDGET_TYPES_BY_SUBJECT = {
    "math": ["numeric-input", "radio", "expression", "dropdown", "input-number", "number-line", "plotter", "interactive-graph"],
    "science": ["radio", "dropdown", "image", "matcher", "categorizer", "orderer", "label-image"],
    "english": ["radio", "dropdown", "matcher", "orderer", "categorizer"],
    "history": ["radio", "dropdown", "matcher", "orderer", "categorizer"],
    "geography": ["radio", "dropdown", "image", "label-image", "matcher"],
    "coding": ["radio", "dropdown", "expression", "orderer"],
}

# Problem types by subject for curriculum coverage
PROBLEM_TYPES_BY_SUBJECT = {
    "math": [
        "Add or subtract",
        "Multiply or divide",
        "Fractions",
        "Decimals",
        "Percentages",
        "Word problems",
        "Patterns and sequences",
        "Geometry",
        "Measurement",
        "Data and probability",
        "Algebraic expressions",
        "Number sense"
    ],
    "science": [
        "Classification",
        "Cause and effect",
        "Observation vs inference",
        "Experiment design",
        "Scientific vocabulary",
        "Diagram labeling",
        "Life cycles",
        "States of matter",
        "Food chains",
        "Weather patterns"
    ],
    "english": [
        "Vocabulary in context",
        "Grammar identification",
        "Reading comprehension",
        "Main idea",
        "Author's purpose",
        "Literary devices",
        "Sentence structure",
        "Parts of speech",
        "Spelling patterns",
        "Figurative language"
    ],
    "history": [
        "Timeline sequencing",
        "Cause and effect",
        "Historical figures",
        "Primary vs secondary sources",
        "Historical vocabulary",
        "Map reading",
        "Cultural comparison",
        "Important events"
    ]
}


@app.post("/api/generate/live")
async def generate_questions_live(request: LiveGenerationRequest):
    """
    Smart question generation with content library.

    Flow:
    1. Check MongoDB for existing questions matching topic/grade/subject (unless force_new=True)
    2. If found enough → return existing (saves API calls)
    3. If not enough → generate new with Gemini
    4. Store new questions in MongoDB for future reuse
    5. Return questions (mix of existing + new if needed)
    """

    # Step 1: Check for existing questions in content library (unless forcing new)
    existing = []
    if not request.force_new:
        search_query = {
            "$or": [
                {"topic": {"$regex": request.prompt, "$options": "i"}},
                {"prompt": {"$regex": request.prompt, "$options": "i"}},
                {"keywords": {"$regex": request.prompt, "$options": "i"}}
            ],
            "grade": request.grade,
            "subject": request.subject
        }
        existing = list(generated_questions.find(search_query).limit(request.count))
        print(f"[CONTENT LIBRARY] Found {len(existing)} existing questions for '{request.prompt}'")
    else:
        print(f"[CONTENT LIBRARY] force_new=True, skipping cache and generating fresh questions")
    
    # If we have enough, return existing questions
    if len(existing) >= request.count:
        print(f"[CONTENT LIBRARY] Using {request.count} existing questions (no generation needed)")
        questions = []
        for q in existing[:request.count]:
            # Extract from perseus_json if that's where it's stored
            perseus_data = q.get("perseus_json", {})
            if not perseus_data:
                # Fallback to direct fields if perseus_json doesn't exist
                perseus_data = q

            widgets = perseus_data.get("question", {}).get("widgets", {})
            fix_numeric_input_widgets(widgets)
            fix_radio_widgets(widgets)
            questions.append({
                "question": perseus_data.get("question", {}),
                "hints": perseus_data.get("hints", []),
                "answerArea": perseus_data.get("answerArea", perseus_data.get("answer_area", {})),
                "itemDataVersion": {"major": 0, "minor": 1},
                "dash_metadata": {
                    "dash_question_id": q.get("question_id"),
                    "source": "content_library",
                    "reused": True
                }
            })
        return questions
    
    # Step 2: Need to generate more questions
    needed = request.count - len(existing)
    print(f"[CONTENT LIBRARY] Generating {needed} new questions...")
    
    if not GENAI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Live generation unavailable - google-generativeai not installed")
    
    try:
        if GENAI_PROVIDER == "google-genai":
            model = None
        else:
            model = genai_model
        
        # Build the generation prompt with subject-specific guidance
        subject_name = request.subject.replace('-', ' ').title()
        
        # Get variety: rotate through widget types and problem types
        import random
        widget_types = WIDGET_TYPES_BY_SUBJECT.get(request.subject.lower(), ["radio", "numeric-input"])
        problem_types = PROBLEM_TYPES_BY_SUBJECT.get(request.subject.lower(), ["General question"])

        # Select problem type first
        selected_problem_type = random.choice(problem_types)

        # Filter widgets based on problem type complexity
        # Simple arithmetic should use simple widgets (avoid expression/plotter/interactive-graph)
        simple_arithmetic_types = ["Add or subtract", "Multiply or divide", "Number sense"]
        if selected_problem_type in simple_arithmetic_types:
            # Filter out complex widgets that cause MathInput issues
            filtered_widgets = [w for w in widget_types if w not in ["expression", "plotter", "interactive-graph"]]
            if filtered_widgets:
                widget_types = filtered_widgets
            # Prefer numeric-input for simple arithmetic if available
            if "numeric-input" in widget_types and random.random() < 0.6:
                selected_widget = "numeric-input"
            else:
                selected_widget = random.choice(widget_types)
        else:
            selected_widget = random.choice(widget_types)

        print(f"[VARIETY] Selected widget: {selected_widget}, problem type: {selected_problem_type}")

        # Get Khan Academy examples for few-shot learning
        ka_examples = ""
        if example_retriever:
            try:
                ka_examples = example_retriever.get_examples_for_prompt(
                    widget_type=selected_widget,
                    topic=request.prompt,
                    num_examples=2
                )
                print(f"[FEW-SHOT] Retrieved {len(ka_examples)} chars of KA examples")
            except Exception as e:
                print(f"[FEW-SHOT] Could not retrieve examples: {e}")
                ka_examples = ""

        # Subject-specific instructions
        subject_guidance = {
            "math": f"Create MATH questions about numbers, arithmetic, counting, shapes, or patterns. Focus on: {selected_problem_type}. Use {selected_widget} widgets.",
            "english": f"Create ENGLISH LANGUAGE questions about spelling, vocabulary, grammar, or reading. Focus on: {selected_problem_type}. Use {selected_widget} widgets.",
            "science": f"Create SCIENCE questions about nature, animals, plants, weather, or the human body. Focus on: {selected_problem_type}. Use {selected_widget} widgets.",
            "coding": f"Create CODING/LOGIC questions about sequences, patterns, or algorithms. Focus on: {selected_problem_type}. Use {selected_widget} widgets."
        }

        subject_instruction = subject_guidance.get(request.subject.lower(), f"Create {subject_name} questions using {selected_widget} widgets.")
        
        # Language handling
        lang_name = LANGUAGE_NAMES.get(request.language, "English")
        lang_instruction = ""
        if request.language != "en":
            lang_instruction = f"""
LANGUAGE: Write ALL user-facing text in {lang_name}.
- Question content must be in {lang_name}
- Answer choices must be in {lang_name}
- Hints must be in {lang_name}
- Keep JSON keys in English (content, widgets, etc.)
- Adapt the tone to be natural in {lang_name}
"""
        
        prompt = f'''You are creating fun, friendly {subject_name} questions for a {request.grade} grade student.

SUBJECT: {subject_name.upper()}
{subject_instruction}
{lang_instruction}

The student wants to learn: "{request.prompt}"

{ka_examples}

Create {needed} questions in the innocent drinks tone of voice:
- use lowercase and casual language. no capital letters at the start (unless it's a name).
- use very short sentences. like this. easy peasy. one idea per sentence.
- be super friendly and encouraging. use phrases like "you've got this", "we believe in you", "no rush".
- add emojis to make it fun (🍪 🌟 ✨ 🎉).
- be chatty and warm. talk directly to the student ("you", "your").
- be gentle and supportive. never pushy or demanding.
- keep it simple and clear. no complicated words.
- IMPORTANT: apply this tone to BOTH the question content AND all hints. hints should be just as friendly and encouraging!

Use the Perseus format structure shown in the examples above.

IMPORTANT: Return ONLY a valid JSON array. No markdown, no explanation.

Each question must have this exact structure:
{{
  "question": {{
    "content": "question text with [[☃ numeric-input 1]] or [[☃ radio 1]] placeholder",
    "widgets": {{
      "numeric-input 1": {{
        "type": "numeric-input",
        "options": {{
          "answers": [{{"value": NUMBER, "status": "correct", "strict": false}}],
          "size": "normal"
        }}
      }}
    }},
    "images": {{}}
  }},
  "hints": [{{"content": "friendly hint", "widgets": {{}}}}],
  "answerArea": {{}},
  "dash_metadata": {{
    "dash_question_id": "gen_live_1",
    "skill_ids": ["live_gen"],
    "topic": "custom"
  }}
}}

For multiple choice, use radio widget:
"radio 1": {{
  "type": "radio",
  "options": {{
    "choices": [
      {{"content": "answer1", "correct": false}},
      {{"content": "answer2", "correct": true}},
      {{"content": "answer3", "correct": false}}
    ],
    "randomize": true
  }}
}}

RULES:
- Use lowercase, be chatty and friendly
- Make it fun and personalized to what they asked
- Include emojis where appropriate
- Widget placeholder MUST be in the content string
- Return ONLY the JSON array, nothing else

Generate {request.count} questions now:'''

        if GENAI_PROVIDER == "google-genai":
            response = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            text = (getattr(response, "text", None) or "").strip()
            if not text:
                text = str(response)
        else:
            response = model.generate_content(prompt)
            text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        
        # Parse JSON
        questions = json.loads(text)
        
        # Ensure it's a list
        if not isinstance(questions, list):
            questions = [questions]
        
        # Add unique IDs and store in MongoDB
        stored_count = 0
        for i, q in enumerate(questions):
            question_id = f"gen_{request.grade}_{request.subject}_{int(time.time())}_{i}"
            
            if "dash_metadata" not in q:
                q["dash_metadata"] = {}
            q["dash_metadata"]["dash_question_id"] = question_id
            q["dash_metadata"]["source"] = "live_generation"
            q["dash_metadata"]["prompt"] = request.prompt[:100]
            
            if "itemDataVersion" not in q:
                q["itemDataVersion"] = {"major": 0, "minor": 1}
            
            # Fix widgets for proper scoring/rendering
            widgets = q.get("question", {}).get("widgets", {})
            fix_numeric_input_widgets(widgets)
            fix_radio_widgets(widgets)
            
            # Step 3: Store in MongoDB with FULL Khan Academy format
            question_data = q.get("question", {})
            hints_data = q.get("hints", [])
            answer_area = q.get("answerArea", {})

            # Generate KA-style IDs
            exercise_id = generate_ka_id()
            lesson_id = generate_ka_id()
            unit_id = generate_ka_id()
            course_id = generate_ka_id()

            # Generate SHA hash of question content
            content_str = json.dumps(question_data, sort_keys=True)
            sha_hash = generate_sha256(content_str)

            # Infer problem type
            problem_type = infer_problem_type(
                question_data.get("content", ""),
                question_data.get("widgets", {})
            )

            # Check if requires screen/mouse
            needs_screen = requires_screen_or_mouse(question_data.get("widgets", {}))

            # Build full answer_area with all calculators
            full_answer_area = {
                "calculator": False,
                "chi2Table": False,
                "financialCalculatorMonthlyPayment": False,
                "financialCalculatorTimeToPayOff": False,
                "financialCalculatorTotalAmount": False,
                "periodicTable": False,
                "periodicTableWithKey": False,
                "tTable": False,
                "zTable": False,
                **answer_area  # Merge any existing answer_area settings
            }

            # Build perseus_json structure (matches KA format exactly)
            perseus_json = {
                "answerArea": full_answer_area,
                "hints": hints_data,
                "question": question_data
            }

            # Build complete document matching Khan Academy schema
            doc_to_store = {
                "question_id": question_id,
                "sha": sha_hash,
                "exercise_id": exercise_id,
                "lesson_id": lesson_id,
                "unit_id": unit_id,
                "course_id": course_id,
                "problem_type": problem_type,
                "perseus_json": perseus_json,
                "requires_screen_or_mouse": needs_screen,
                "downloaded_at": datetime.utcnow(),
                "appears_in_exercises": [exercise_id],
                "order_in_exercise": i,
                # Additional metadata for our use
                "grade": request.grade,
                "subject": request.subject,
                "topic": request.prompt.lower(),
                "prompt": request.prompt,
                "language": request.language,
                "keywords": request.prompt.lower().split(),
                "widget_types": list(question_data.get("widgets", {}).keys()),
                "created_at": datetime.utcnow(),
                "source": "gemini_generated",
                "generator_model": "gemini-2.0-flash",
                "reuse_count": 0
            }
            try:
                generated_questions.insert_one(doc_to_store)
                stored_count += 1
            except Exception as store_err:
                print(f"[CONTENT LIBRARY] Failed to store question: {store_err}")
        
        print(f"[CONTENT LIBRARY] Stored {stored_count} new questions in MongoDB")
        
        # Step 4: Combine existing + new questions
        result = []
        
        # Add existing questions first
        for q in existing:
            # Extract from perseus_json if that's where it's stored
            perseus_data = q.get("perseus_json", {})
            if not perseus_data:
                # Fallback to direct fields if perseus_json doesn't exist
                perseus_data = q

            widgets = perseus_data.get("question", {}).get("widgets", {})
            fix_numeric_input_widgets(widgets)
            fix_radio_widgets(widgets)
            result.append({
                "question": perseus_data.get("question", {}),
                "hints": perseus_data.get("hints", []),
                "answerArea": perseus_data.get("answerArea", perseus_data.get("answer_area", {})),
                "itemDataVersion": {"major": 0, "minor": 1},
                "dash_metadata": {
                    "dash_question_id": q.get("question_id"),
                    "source": "content_library",
                    "reused": True
                }
            })
        
        # Add newly generated questions
        result.extend(questions)
        
        print(f"[CONTENT LIBRARY] Returning {len(result)} questions ({len(existing)} reused + {len(questions)} new)")
        return result[:request.count]
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response: {text[:500]}")
        raise HTTPException(status_code=500, detail="Failed to parse generated questions")
    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")


# ============================================
# CONTENT LIBRARY STATS
# ============================================

@app.get("/api/content-library/stats")
def get_content_library_stats():
    """Get stats about the content library."""
    total = generated_questions.count_documents({})
    
    # By grade
    by_grade = {}
    for grade in ["K-2", "3-5", "6-8", "9-12"]:
        by_grade[grade] = generated_questions.count_documents({"grade": grade})
    
    # By subject
    by_subject = {}
    for subject in ["math", "english", "science", "coding"]:
        by_subject[subject] = generated_questions.count_documents({"subject": subject})
    
    # Recent topics
    pipeline = [
        {"$group": {"_id": "$topic", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_topics = list(generated_questions.aggregate(pipeline))
    
    return {
        "total_questions": total,
        "by_grade": by_grade,
        "by_subject": by_subject,
        "top_topics": [{"topic": t["_id"], "count": t["count"]} for t in top_topics]
    }


# ============================================
# MEMORY-AWARE QUESTION GENERATION
# ============================================

@app.post("/api/generate/personalized")
async def generate_personalized_questions(
    request: LiveGenerationRequest,
    student_id: str = None
):
    """
    Generate questions personalized with student memories.
    
    Uses:
    - Student's interests (pets, hobbies, favorite things)
    - Learning history
    - Emotional context
    """
    # Get student memories if available
    personalization_context = ""
    
    if student_id:
        # Try v1-memory personalizer first
        try:
            from content.memory_personalizer import MemoryPersonalizer
            personalizer = MemoryPersonalizer()
            personalization_context = personalizer.get_personalization_prompt(student_id)
        except Exception as e:
            print(f"[MEMORY] v1-memory personalizer unavailable: {e}")
            # Fallback to basic MongoDB memories
            mem_query = {"student_id": student_id}
            student_memories = list(db["memories"].find(mem_query).limit(5))

            if student_memories:
                personalization_context = "\n\nPERSONALIZATION (use these details in questions):\n"
                for mem in student_memories:
                    mem_type = mem.get("type", "general")
                    mem_text = mem.get("text", "")[:100]
                    if mem_type == "personal":
                        personalization_context += f"- Personal: {mem_text}\n"
                    elif mem_type == "preference":
                        personalization_context += f"- Likes: {mem_text}\n"
    
    # Call the regular generation with personalization context
    # For now, just add to the prompt
    enhanced_prompt = request.prompt
    if personalization_context:
        enhanced_prompt = f"{request.prompt}{personalization_context}"
    
    # Create modified request
    modified_request = LiveGenerationRequest(
        prompt=enhanced_prompt,
        grade=request.grade,
        subject=request.subject,
        language=request.language,
        count=request.count,
        force_new=request.force_new
    )
    
    return await generate_questions_live(modified_request)


# Run with: python content/api.py
if __name__ == "__main__":
    print("🚀 CONTENT API v2.0 - Starting with ALL endpoints including /api/generate/live")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
