
import sys
import os
from bson import ObjectId
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

IDS_TO_INSPECT = {
    "Code Question": "6933d8a945a4cb2e2ed4450b"
}

def inspect():
    print("INSPECTING QUESTION DATA...\n")
    
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

            print(f"CONTENT:\n{content}")
            
            print("\nWIDGETS:")
            for w_name, w_data in widgets.items():
                w_type = w_data.get('type')
                print(f"  - {w_name} ({w_type}):")
                print(f"    Options: {w_data.get('options', {})}")

        except Exception as e:
            print(f"❌ ERROR: {e}")
        print("\n")

if __name__ == "__main__":
    inspect()
