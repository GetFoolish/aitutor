
import sys
import os
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

IDS_TO_CHECK = [
    "692fac057e334152c5f473e5", # interactive-graph
    "692f1731f13be434de20c0c6", # numeric-input
    "692f198f0a3ad6a639ce934d", # radio
    "692fb45f7e334152c5f474d2", # dropdown
    "692f1792f13be434de20c0d1"  # image
]

def verify():
    print("VERIFYING IDs IN DATABASE...")
    count = mongo_db.scraped_questions.count_documents({})
    print(f"Total questions in DB: {count}")
    
    for qid in IDS_TO_CHECK:
        try:
            doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(qid)})
            if doc:
                print(f"✅ Found {qid}")
            else:
                print(f"❌ NOT FOUND {qid}")
        except Exception as e:
            print(f"❌ Error checking {qid}: {e}")

if __name__ == "__main__":
    verify()
