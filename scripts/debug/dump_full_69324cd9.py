import os
import sys
import json
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

def dump_question():
    qid = "69324cd92e5f91c2481807bc"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print("Question not found.")
        return
    
    doc['_id'] = str(doc['_id'])
    print(json.dumps(doc, indent=2, cls=DateTimeEncoder))

if __name__ == "__main__":
    dump_question()
