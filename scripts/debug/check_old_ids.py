
import sys
import os
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

IDS_TO_CHECK = [
    "691c6d6a41372912898cd7ae",
    "691c6e2f41372912898cd98d",
    "691c693241372912898ccd8b",
    "691c6ace41372912898cd1fb",
    "691c6d7741372912898cd7d5"
]

def verify():
    print("VERIFYING REQUESTED IDs IN DATABASE...")
    count = mongo_db.scraped_questions.count_documents({})
    print(f"Total questions in DB: {count}")
    
    for qid in IDS_TO_CHECK:
        try:
            if not ObjectId.is_valid(qid):
                 print(f"❌ INVALID FORMAT {qid}")
                 continue

            doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(qid)})
            if doc:
                print(f"✅ FOUND {qid}")
            else:
                print(f"❌ NOT FOUND {qid}")
        except Exception as e:
            print(f"❌ Error checking {qid}: {e}")

if __name__ == "__main__":
    verify()
