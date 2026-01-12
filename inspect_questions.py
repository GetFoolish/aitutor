#!/usr/bin/env python3
"""
Investigate actual Perseus question structure in MongoDB
"""
import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from managers.mongodb_manager import MongoDBManager

def main():
    mongo = MongoDBManager()
    
    print("\n" + "="*80)
    print("INVESTIGATING PERSEUS QUESTIONS IN questions_db")
    print("="*80)
    
    # Get 3 sample questions
    questions = list(mongo.questions.find().limit(3))
    
    for i, q in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"QUESTION {i}")
        print('='*80)
        
        print(f"\nQuestion ID: {q.get('question_id', 'N/A')}")
        print(f"Exercise ID: {q.get('exercise_id', 'N/A')}")
        
        # Check top-level fields
        print(f"\nTop-level fields: {list(q.keys())}")
        
        # Check perseus_json
        perseus_json = q.get('perseus_json', {})
        if perseus_json:
            print(f"\nperseus_json fields: {list(perseus_json.keys())}")
            
            # Check for answer-related fields
            print(f"\nChecking for answer keys:")
            print(f"  - 'answer' field: {('answer' in perseus_json)}")
            print(f"  - 'answers' field: {('answers' in perseus_json)}")
            print(f"  - 'answerArea' field: {('answerArea' in perseus_json)}")
            
            if 'answer' in perseus_json:
                print(f"\n  Answer value: {json.dumps(perseus_json['answer'], indent=2)[:500]}")
            
            if 'answers' in perseus_json:
                print(f"\n  Answers value: {json.dumps(perseus_json['answers'], indent=2)[:500]}")
            
            # Check answerArea
            answer_area = perseus_json.get('answerArea', {})
            if answer_area:
                print(f"\n  answerArea fields: {list(answer_area.keys())}")
                if 'calculator' in answer_area:
                    print(f"    - calculator: {answer_area['calculator']}")
                if 'type' in answer_area:
                    print(f"    - type: {answer_area['type']}")
            
            # Check question content
            question_content = perseus_json.get('question', {})
            if question_content:
                print(f"\n  question fields: {list(question_content.keys())}")
                
                # Check widgets
                widgets = question_content.get('widgets', {})
                if widgets:
                    print(f"\n  Found {len(widgets)} widgets:")
                    for widget_key, widget_data in list(widgets.items())[:2]:  # First 2 widgets
                        print(f"\n    Widget: {widget_key}")
                        print(f"      type: {widget_data.get('type', 'N/A')}")
                        print(f"      fields: {list(widget_data.keys())}")
                        
                        # Check options (for multiple choice)
                        options = widget_data.get('options', {})
                        if options:
                            choices = options.get('choices', [])
                            if choices:
                                print(f"      choices count: {len(choices)}")
                                for idx, choice in enumerate(choices[:2]):  # First 2 choices
                                    print(f"        Choice {idx}: {list(choice.keys())}")
                                    print(f"          correct: {choice.get('correct', 'N/A')}")
                                    print(f"          content: {str(choice.get('content', ''))[:80]}")
        else:
            print("\n  ⚠️ NO perseus_json found!")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
