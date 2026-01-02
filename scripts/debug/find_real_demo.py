
import sys
import os
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_best_demo_questions():
    """Find best available questions for demo from real DB."""
    print("SEARCHING REAL DATABASE FOR DEMO QUESTIONS...")
    
    # Widgets we need for the demo
    target_widgets = [
        'interactive-graph', 
        'numeric-input', 
        'radio', 
        'dropdown',
        'image'
    ]
    
    found = {}
    
    for widget in target_widgets:
        print(f"Searching for {widget}...")
        # Query for questions containing this widget type in proper nested structure
        # Check both top-level 'question.widgets' and 'assessmentData...widgets'
        query = {
            '$or': [
                {f'question.widgets': {'$exists': True}},
                {'assessmentData.data.assessmentItem.item.itemData': {'$exists': True}}
            ]
        }
        
        # We fetch a batch and filter in python to find the specific widget, 
        # as deep nesting queries can be slow or complex if structure varies
        cursor = mongo_db.scraped_questions.find(query).limit(1000)
        
        for doc in cursor:
            # Extract widgets dict
            widgets = {}
            if 'question' in doc and 'widgets' in doc['question']:
                widgets = doc['question']['widgets']
            elif 'assessmentData' in doc:
                try:
                    widgets = doc['assessmentData']['data']['assessmentItem']['item']['itemData']['question']['widgets']
                except:
                    pass
            
            # Check if this widget type exists in this question
            for k, v in widgets.items():
                if v.get('type') == widget:
                    # Found one!
                    obj_id = str(doc['_id'])
                    found[widget] = obj_id
                    print(f"  ✅ Found {widget}: {obj_id}")
                    break
            
            if widget in found:
                break
    
    print("\nRESULTS - USE THESE IDs FOR VIDEO:")
    for w, mid in found.items():
        print(f"{w}: http://localhost:3000/question/{mid}")

if __name__ == "__main__":
    find_best_demo_questions()
