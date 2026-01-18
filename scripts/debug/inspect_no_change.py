
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_no_change():
    qid = "6930bb8a7fa3741ee33a3c10"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if doc:
        print(repr(doc['question']['content']))

if __name__ == "__main__":
    inspect_no_change()
