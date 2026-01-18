
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def compare_formatting():
    q1_id = "6935b50304cecc1435319657" # Fixed one
    q2_id = "69360b810aabe66864660c1a" # New one
    
    for qid in [q1_id, q2_id]:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
        if doc:
            print(f"\n--- Question {qid} ---")
            print(repr(doc['question']['content']))

if __name__ == "__main__":
    compare_formatting()
