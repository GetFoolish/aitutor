
import os
import sys
import json
from bson.objectid import ObjectId

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from managers.mongodb_manager import mongo_db

def inspect_69360b81():
    qid = "69360b810aabe66864660c1a"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print("Question not found")
        return
        
    print("--- CONTENT ---")
    print(doc['question']['content'])
    print("--- WIDGETS ---")
    print(json.dumps(doc['question']['widgets'], indent=2))
    print("--- HINTS ---")
    print(json.dumps(doc.get('hints', []), indent=2))

if __name__ == "__main__":
    inspect_69360b81()
