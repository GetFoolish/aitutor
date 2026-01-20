
import os
import sys
import json
from bson import ObjectId

# Add project root to path for shared imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_bar_chart():
    qid = "6933055bd8006a4430ca39e6"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if doc:
        print(f"\nFULL WIDGETS DUMP FOR {qid}:", flush=True)
        widgets = doc.get('question', {}).get('widgets', {})
        print(json.dumps(widgets, indent=2), flush=True)
    else:
        print(f"Question {qid} not found.", flush=True)

if __name__ == "__main__":
    inspect_bar_chart()
