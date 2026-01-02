
import sys
import os
from bson import ObjectId
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

IDS_TO_INSPECT = {
    "Chart Source (692fa...)": "692fac057e334152c5f473e5"
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

            # Extract content
            content = "N/A"
            if 'question' in doc and 'content' in doc['question']:
                content = doc['question']['content']
            elif 'assessmentData' in doc:
                try:
                    content = doc['assessmentData']['data']['assessmentItem']['item']['itemData']['question']['content']
                except:
                    pass

            print(f"CONTENT:\n{content}")

            # Inspect Widgets
            widgets = {}
            if 'question' in doc and 'widgets' in doc['question']:
                widgets = doc['question']['widgets']
            elif 'assessmentData' in doc:
                try:
                    widgets = doc['assessmentData']['data']['assessmentItem']['item']['itemData']['question']['widgets']
                except:
                    pass
            
            print(f"\nWIDGETS ({len(widgets)}):")
            for wid, wdata in widgets.items():
                print(f"--- {wid} ({wdata.get('type')}) ---")
                options = wdata.get('options', {})
                print(f"Options: {json.dumps(options, indent=2)[:500]}...")

            # Check hints if any
            hints = doc.get('hints', [])
            if not hints and 'assessmentData' in doc:
                 try:
                    hints = doc['assessmentData']['data']['assessmentItem']['item']['itemData']['hints']
                 except:
                     pass
            
            print(f"\nHINTS ({len(hints)}):")
            for i, h in enumerate(hints):
                c = h.get('content', 'N/A')
                print(f"Hint {i+1}: {c[:200]}...")

        except Exception as e:
            print(f"❌ ERROR: {e}")
        print("\n")

if __name__ == "__main__":
    inspect()
