import os
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Correctly escape literal bars and provide specific sequences
# We want to find: ||, \left|\left|, etc.
# In Python r"\|\|" becomes literal \|\| for MongoDB regex
patterns = [
    r"\\left\\\|\\left\\\|",
    r"\\left\\\| \\left\\\|",
    r"\\\|\\\|\s*\\vec",
    r"\\vec\b.*\\\|\\\|", 
    r"\\\|\\\|.*\\vec",     
    r"\\right\\\|\\\|",
    r"\\right\\\|\\\|",
    r"\\right\\\|\|",  # Looking for literal \right| followed by |
    r"\\right\\\|\\\|"
]

# Even simpler: search for what was actually problematic
simple_patterns = [
    r"\\left\|\\left\|",
    r"\|\|\\vec",
    r"Ôÿâ"
]

collections = ['questions', 'scraped_questions']

print("Searching for REAL vector magnitude issues (FIXED REGEX)...")

all_problematic_ids = []

for coll_name in collections:
    coll = db[coll_name]
    
    # We'll use a very simple regex to avoid complexity errors
    query = {
        "$or": [
            {"question.content": {"$regex": r"\\left\|\\left\||\|\|\\vec|Ôÿâ"}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"\\left\|\\left\||\|\|\\vec|Ôÿâ"}},
            {"hints.content": {"$regex": r"\\left\|\\left\||\|\|\\vec|Ôÿâ"}}
        ]
    }
    
    cursor = coll.find(query, {"_id": 1})
    
    ids = [str(doc['_id']) for doc in cursor]
    print(f"Found {len(ids)} in {coll_name}")
    if len(ids) > 0 and len(ids) < 100:
        print(f"IDs: {ids}")
    elif len(ids) >= 100:
        print(f"Example IDs: {ids[:10]}")
    
    all_problematic_ids.extend([(coll_name, id) for id in ids])

print(f"\nTotal real potential issues found: {len(all_problematic_ids)}")
