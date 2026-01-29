#!/usr/bin/env python3
"""
Test script to load converted Perseus questions into MongoDB and verify rendering.

Usage:
    python scripts/test_converted_questions.py scripts/test_output_perseus.json
"""

import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient


def get_mongo_client():
    """Get MongoDB client from environment."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("MONGODB_URI not set in environment")
    return MongoClient(uri)


def load_questions_to_mongodb(questions: list, collection_name: str = "test_converted_questions"):
    """Load converted questions into MongoDB for testing."""
    client = get_mongo_client()
    db = client.get_database("questions_db")
    collection = db[collection_name]
    
    # Clear existing test questions
    collection.delete_many({})
    
    # Insert questions with proper structure
    inserted_ids = []
    for i, q in enumerate(questions):
        doc = {
            "question_id": q.get("questionId", f"test_q_{i}"),
            "perseus_json": {
                "question": q.get("question", {}),
                "answerArea": q.get("answerArea", {}),
                "hints": q.get("hints", []),
                "itemDataVersion": q.get("itemDataVersion", {})
            },
            "metadata": q.get("_metadata", {}),
            "created_at": datetime.now(),
            "source": "converter_test"
        }
        result = collection.insert_one(doc)
        inserted_ids.append(str(result.inserted_id))
        print(f"✅ Inserted question {i+1}: {doc['question_id']}")
    
    print(f"\n📊 Inserted {len(inserted_ids)} questions into {collection_name}")
    return inserted_ids


def validate_perseus_structure(question: dict) -> list:
    """Validate that a question has correct Perseus structure."""
    errors = []
    
    # Check required top-level fields
    if "question" not in question:
        errors.append("Missing 'question' field")
    if "hints" not in question:
        errors.append("Missing 'hints' field")
    if "answerArea" not in question:
        errors.append("Missing 'answerArea' field")
    
    # Check question structure
    q = question.get("question", {})
    if "content" not in q:
        errors.append("Missing 'question.content' field")
    if "widgets" not in q:
        errors.append("Missing 'question.widgets' field")
    
    # Check widgets structure
    widgets = q.get("widgets", {})
    for widget_id, widget in widgets.items():
        if "type" not in widget:
            errors.append(f"Widget '{widget_id}' missing 'type'")
        if "options" not in widget:
            errors.append(f"Widget '{widget_id}' missing 'options'")
        elif not isinstance(widget["options"], dict):
            errors.append(f"Widget '{widget_id}' options is not an object (got {type(widget['options']).__name__})")
    
    # Check hints structure
    hints = question.get("hints", [])
    for i, hint in enumerate(hints):
        if not isinstance(hint, dict):
            errors.append(f"Hint {i} is not an object")
        elif "content" not in hint:
            errors.append(f"Hint {i} missing 'content'")
    
    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_converted_questions.py <perseus_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    print(f"🔍 Loading questions from {input_file}...")
    with open(input_file, 'r') as f:
        questions = json.load(f)
    
    print(f"📋 Found {len(questions)} questions\n")
    
    # Validate each question
    all_valid = True
    for i, q in enumerate(questions):
        errors = validate_perseus_structure(q)
        if errors:
            print(f"❌ Question {i+1} validation errors:")
            for err in errors:
                print(f"   - {err}")
            all_valid = False
        else:
            print(f"✅ Question {i+1} ({q.get('questionId', 'unknown')}) - Valid Perseus structure")
            
            # Show widget types
            widgets = q.get("question", {}).get("widgets", {})
            for wid, w in widgets.items():
                wtype = w.get("type", "unknown")
                opts = w.get("options", {})
                print(f"   └─ {wid}: type={wtype}, options={list(opts.keys())}")
    
    print()
    
    if not all_valid:
        print("❌ Some questions have validation errors. Fix before loading to MongoDB.")
        sys.exit(1)
    
    # Ask to load to MongoDB
    print("All questions validated successfully!")
    response = input("\nLoad to MongoDB for frontend testing? (y/n): ").strip().lower()
    
    if response == 'y':
        try:
            load_questions_to_mongodb(questions)
            print("\n✅ Questions loaded! You can now test in the frontend.")
            print("   Note: These are in 'test_converted_questions' collection.")
        except Exception as e:
            print(f"❌ MongoDB error: {e}")
            sys.exit(1)
    else:
        print("Skipped MongoDB loading.")


if __name__ == "__main__":
    main()
