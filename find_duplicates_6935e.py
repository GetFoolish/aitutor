import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=20000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Search patterns based on unique content features
patterns = [
    r"negative seven, six",
    r"point two, negative five",
    r"point seven, two",
    r"f\(2\)"
]

print("Searching for duplicates of 6935e15e...")

duplicate_ids = {}

for coll_name in ['questions', 'scraped_questions']:
    print(f"Checking {coll_name}...")
    coll = db[coll_name]
    
    # Target content and inner itemData
    cursor = coll.find({
        "$or": [
            {"question.content": {"$regex": "negative seven, six"}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "negative seven, six"}}
        ]
    }, {"_id": 1})
    
    ids = [str(doc['_id']) for doc in cursor]
    if ids:
        duplicate_ids[coll_name] = ids
        print(f"Found {len(ids)} duplicates in {coll_name}")
        print(f"IDs: {ids}")

print("\nFinal Duplicate List:")
print(json.dumps(duplicate_ids, indent=2))
