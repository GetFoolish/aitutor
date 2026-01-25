import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

MONGO_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME') or 'ai_tutor'

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

question_id = "693199158189149cdbee41a8"
COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print(f"Fixing question {question_id} in {COLLECTION_NAME}...")

item = collection.find_one({"_id": ObjectId(question_id)})
if not item:
    print("Question not found as ObjectId, trying as string...")
    item = collection.find_one({"_id": question_id})

if not item:
    print("Question not found.")
    exit(1)

def fix_string(s):
    if not isinstance(s, str):
        return s
    
    # 1. Fix mismatched bars: \left|\left| ... \right\| -> \left\| ... \right\|
    # Note: in Python strings, we need to handle backslashes carefully
    # Original problematic strings seen in JSON:
    # "\\left|\\left|5 \\vec v\\right\\|"
    
    # Check for direct matches first
    s = s.replace(r"\left|\left|", r"\left\|")
    s = s.replace(r"\right\|", r"\right\|") # This might be correct already but let's be sure
    
    # Also handle variants with different spacing
    s = s.replace(r"\left| \left|", r"\left\|")
    
    # Ensure it's \left\| ... \right\|
    # If we have \left\| and only \right|, we must close it properly
    if r"\left\|" in s and r"\right|" in s and r"\right\|" not in s:
        s = s.replace(r"\right|", r"\right\|")

    # 2. Fix snowflake encoding: Ôÿâ -> ☃
    s = s.replace("Ôÿâ", "☃")
    
    return s

def process_nested(obj):
    if isinstance(obj, dict):
        return {k: process_nested(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_nested(i) for i in obj]
    elif isinstance(obj, str):
        return fix_string(obj)
    else:
        return obj

# Process the whole item
fixed_item = process_nested(item)

# Specific check for the most critical string
content = fixed_item.get('question', {}).get('content', '')
print(f"New question content: {content}")

# Update in DB
result = collection.replace_one({"_id": item["_id"]}, fixed_item)
print(f"Update result: matched={result.matched_count}, modified={result.modified_count}")

# Verify other collections just in case
for coll_name in ['questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        it = coll.find_one({"_id": ObjectId(question_id)})
    except:
        it = coll.find_one({"_id": question_id})
        
    if it:
        print(f"Also found in {coll_name}, fixing there too...")
        fixed_it = process_nested(it)
        coll.replace_one({"_id": it["_id"]}, fixed_it)
        print(f"Fixed in {coll_name}")
