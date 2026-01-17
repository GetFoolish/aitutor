
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_id_type():
    qid = "69317f2c47a2cb48fc68c308"
    
    print(f"Checking {qid}...")
    
    # Check ObjectId
    try:
        obj_id = ObjectId(qid)
        doc_obj = mongo_db.scraped_questions.find_one({"_id": obj_id})
        if doc_obj:
            print("Found with ObjectId!")
            print(f"Content: {doc_obj.get('question', {}).get('content', '')[:50]}")
        else:
            print("Not found with ObjectId.")
    except Exception as e:
        print(f"Invalid ObjectId: {e}")
        
    # Check String
    doc_str = mongo_db.scraped_questions.find_one({"_id": qid})
    if doc_str:
        print("Found with String ID!")
        print(f"Content: {doc_str.get('question', {}).get('content', '')[:50]}")
    else:
        print("Not found with String ID.")

if __name__ == "__main__":
    inspect_id_type()
