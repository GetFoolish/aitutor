
import sys
import os
from bson import ObjectId
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

IDS_TO_INSPECT = {
    "Graph (692fac...)": "692fac057e334152c5f473e5",
    "Radio (692f19...)": "692f198f0a3ad6a639ce934d",
    "Dropdown (692fb4...)": "692fb45f7e334152c5f474d2",
    "Numeric/Format (692f17...)": "692f1731f13be434de20c0c6"
}

def inspect():
    print("INSPECTING REAL QUESTION DATA...\n")
    
    for label, qid in IDS_TO_INSPECT.items():
        print(f"--- {label} ---")
        try:
            doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(qid)})
            if not doc:
                print("❌ NOT FOUND")
                continue

            # Extract content and widgets safely
            content = "N/A"
            widgets = {}
            
            # Athena format
            if 'question' in doc and 'content' in doc['question']:
                content = doc['question']['content']
                widgets = doc['question'].get('widgets', {})
            # Perseus format nested
            elif 'assessmentData' in doc:
                try:
                    q_data = doc['assessmentData']['data']['assessmentItem']['item']['itemData']['question']
                    content = q_data['content']
                    widgets = q_data['widgets']
                except:
                    pass

            print(f"CONTENT: {content[:150]}...") # First 150 chars
            
            print("WIDGETS:")
            for w_name, w_data in widgets.items():
                w_type = w_data.get('type')
                print(f"  - {w_name} ({w_type}):")
                
                # Check specific feedback points
                options = w_data.get('options', {})
                if w_type == 'radio':
                    choices = options.get('choices', [])
                    print(f"    Choices: {[c.get('content', 'N/A') for c in choices]}")
                elif w_type == 'interactive-graph':
                    print(f"    Graph Type: {options.get('graph', {}).get('type')}")
                    print(f"    Labels: {options.get('labels')}")
                elif w_type == 'dropdown':
                    choices = options.get('choices', [])
                    print(f"    Choices: {[c.get('content', 'N/A') for c in choices]}")

        except Exception as e:
            print(f"❌ ERROR: {e}")
        print("\n")

if __name__ == "__main__":
    inspect()
