import os
import json
import re
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Pattern: \begin{align} or \begin{aligned} followed eventually by \underline and \end{...}
# These are likely the vertical addition problems
FIND_PATTERN = r"\\begin\{align\}[\s\S]*?\\underline\{[\s\S]*?\\end\{align\}"
# Note: In Mongo we use regex search on the content fields

print("Scanning for all vertical addition LaTeX bugs...")

found_ids = {}

for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    print(f"Checking {coll_name}...")
    coll = db[coll_name]
    try:
        # Search content and itemData
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": r"\\begin\{align\}.*?\\underline"}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"\\begin\{align\}.*?\\underline"}}
            ]
        }, {"_id": 1})
        
        ids = [str(doc['_id']) for doc in cursor]
        if ids:
            found_ids[coll_name] = ids
            print(f"  Found {len(ids)} in {coll_name}")
    except Exception as e:
        print(f"  Error: {e}")

print("\nFull Bug Report (IDs):")
print(json.dumps(found_ids, indent=2))
