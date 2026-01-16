
import os
import sys
import json
from bson.objectid import ObjectId

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def dump_widgets():
    qid = "69343959e9b1bbd2029fbbf2"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print("Not found")
        return

    print("--- WIDGETS ---")
    print(json.dumps(doc.get('question', {}).get('widgets', {}), indent=2))
    
if __name__ == "__main__":
    dump_widgets()
