import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=30000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Search patterns based on unique content features
patterns = [
    r"Mediterranean forests, woodlands, and scrub biome",
    r"Baja California Peninsula",
    r"Troodos National Forest Park"
]

print("Searching for duplicates of 692fb4ae...")

duplicate_ids = {}

for coll_name in ['questions', 'scraped_questions']:
    print(f"Checking {coll_name}...")
    coll = db[coll_name]
    
    cursor = coll.find({
        "$or": [
            {"question.content": {"$regex": "Mediterranean forests, woodlands, and scrub biome"}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "Mediterranean forests, woodlands, and scrub biome"}}
        ]
    }, {"_id": 1})
    
    ids = [str(doc['_id']) for doc in cursor]
    if ids:
        duplicate_ids[coll_name] = ids
        print(f"Found {len(ids)} duplicates in {coll_name}")
        print(f"IDs: {ids}")

print("\nFinal Duplicate List:")
print(json.dumps(duplicate_ids, indent=2))
