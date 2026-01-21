#!/usr/bin/env python3
"""
Find all questions with triangle images that might have dark mode visibility issues.
"""

from pymongo import MongoClient
import json

def find_triangle_questions():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['athena_db']
    
    # First, get the problematic question to understand its structure
    problem_question = db.questions.find_one({'_id': '6932160533f9a4d79a00653d'})
    
    print("=== Problematic Question ===")
    print(f"ID: {problem_question['_id']}")
    print(f"Question: {problem_question.get('question', 'N/A')[:100]}...")
    
    # Extract the image URL/hash from the problem question
    if 'widgets' in problem_question:
        for widget in problem_question['widgets']:
            if widget.get('type') == 'image':
                print(f"\nImage widget found:")
                print(f"  backgroundImage: {widget.get('options', {}).get('backgroundImage', {})}")
    
    # Search for similar questions with triangle-related content
    print("\n=== Searching for similar triangle questions ===")
    
    # Search patterns
    patterns = [
        {'question': {'$regex': 'triangle', '$options': 'i'}},
        {'widgets.type': 'image', 'widgets.options.backgroundImage.url': {'$regex': 'triangle', '$options': 'i'}},
    ]
    
    all_triangle_questions = []
    
    for pattern in patterns:
        questions = list(db.questions.find(pattern))
        all_triangle_questions.extend(questions)
    
    # Remove duplicates
    unique_questions = {q['_id']: q for q in all_triangle_questions}
    
    print(f"\nFound {len(unique_questions)} unique triangle-related questions:")
    
    for qid, question in unique_questions.items():
        print(f"\n  ID: {qid}")
        print(f"  Question: {question.get('question', 'N/A')[:80]}...")
        
        # Check for image widgets
        if 'widgets' in question:
            for widget in question['widgets']:
                if widget.get('type') == 'image':
                    bg_image = widget.get('options', {}).get('backgroundImage', {})
                    if bg_image:
                        print(f"    Image URL: {bg_image.get('url', 'N/A')}")
    
    return list(unique_questions.keys())

if __name__ == '__main__':
    triangle_ids = find_triangle_questions()
    print(f"\n=== Summary ===")
    print(f"Total triangle questions found: {len(triangle_ids)}")
    print(f"IDs: {triangle_ids}")
