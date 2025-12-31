import sys
import os

# Add the project root and service directory to path
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./services/athenaAPI'))

import dotenv
dotenv.load_dotenv()

from services.athenaAPI.app.question_loader import get_questions
import json

def verify():
    print("--- Testing 'numeric-input' filter ---")
    questions = get_questions(sample_size=5, widget_types=['numeric-input'])
    print(f"Got {len(questions)} questions")
    for i, q in enumerate(questions):
        print(f"Q{i+1}: ID={q['_id']}, Types={q['widgetTypes']}")
        # Check if it has any interactive widgets other than numeric-input
        interactive_types = {'radio', 'dropdown', 'numeric-input', 'input-number', 'expression'}
        found_interactive = set(q['widgetTypes']) & interactive_types
        print(f"   Interactive types found: {found_interactive}")

    print("\n--- Testing 'radio' filter ---")
    questions = get_questions(sample_size=5, widget_types=['radio'])
    print(f"Got {len(questions)} questions")
    for i, q in enumerate(questions):
        print(f"Q{i+1}: ID={q['_id']}, Types={q['widgetTypes']}")
        found_interactive = set(q['widgetTypes']) & interactive_types
        print(f"   Interactive types found: {found_interactive}")

if __name__ == "__main__":
    verify()
