
import os
import sys
import json
from bson import ObjectId

# Add project root to path
original_cwd = os.getcwd()
project_root = original_cwd
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services', 'athenaAPI'))

try:
    from managers.mongodb_manager import mongo_db
    from app.question_loader import get_question_by_id
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--id", required=True)
args = parser.parse_args()

id_str = args.id
print(f"DEEP INSPECT FOR ID: {id_str}")

try:
    # Try searching in raw scraped_questions if get_question_by_id fails or returns limited data
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str}) or \
          mongo_db.scraped_questions.find_one({"questionId": id_str})
    
    if not doc:
        print("❌ FAILURE: Question not found in database.")
    else:
        print(f"Found document with ID: {doc.get('_id')}")
        print(f"Widget Types: {doc.get('widgetTypes')}")
        
        # Analyze question content
        question = doc.get('question', {})
        print(f"Content: {question.get('content')}")
        
        widgets = question.get('widgets', {})
        print(f"TOTAL WIDGETS: {len(widgets)}")
        for w_id, w_data in widgets.items():
            print(f"  - Widget {w_id} ({w_data.get('type')})")
            if w_data.get('type') == 'interactive-graph':
                print(f"    - Options: {json.dumps(w_data.get('options', {}), indent=2)}")
            elif w_data.get('type') == 'image':
                print(f"    - Image URL: {w_data.get('options', {}).get('backgroundImage', {}).get('url')}")
            else:
                # Print options for other widgets to see what's happening
                print(f"    - Options: {json.dumps(w_data.get('options', {}), indent=2)}")

except Exception as e:
    print(f"🔥 CRASH during deep inspect: {e}")
    import traceback
    traceback.print_exc()
