import os
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Very specific patterns for magnitude of vectors that might be broken
patterns = [
    r"\\left\|\\left\|",
    r"\\left\| \\left\|",
    r"\|\|\s*\\vec",
    r"\\vec\b.*\|\|", # \vec something ||
    r"\|\|.*\vec",     # || something \vec
    r"\\right\|\|",
    r"\\right\||",
    r"\\right\|\\|"
]

collections = ['questions', 'scraped_questions']

print("Searching for REAL vector magnitude issues...")

all_problematic_ids = []

for coll_name in collections:
    coll = db[coll_name]
    cursor = coll.find({
        "$or": [
            {"question.content": {"$regex": "|".join(patterns)}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "|".join(patterns)}},
            {"hints.content": {"$regex": "|".join(patterns)}}
        ]
    }, {"_id": 1})
    
    ids = [str(doc['_id']) for doc in cursor]
    print(f"Found {len(ids)} in {coll_name}")
    if len(ids) > 0 and len(ids) < 100:
        print(f"IDs: {ids}")
    elif len(ids) >= 100:
        print(f"Example IDs: {ids[:10]}")
    
    all_problematic_ids.extend([(coll_name, id) for id in ids])

print(f"\nTotal potential issues found: {len(all_problematic_ids)}")
