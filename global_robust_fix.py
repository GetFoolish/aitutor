import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def solve_latex(s):
    if not isinstance(s, str):
        return s
    
    # 1. Standardize magnitude to \left\Vert ... \right\Vert
    # Handle variations and broken syntax
    s = s.replace(r"\right|\|", r"\right\Vert")
    s = s.replace(r"\right\||", r"\right\Vert")
    s = s.replace(r"\right\=", r"\right\Vert =")
    
    # Standardize all magnitude opens (common variants)
    s = re.sub(r'\\+left\|\\+left\|', r'\\left\\Vert ', s)
    s = re.sub(r'\\+left\| \\+left\|', r'\\left\\Vert ', s)
    s = re.sub(r'\\+left\\\|', r'\\left\\Vert ', s)
    
    # Correct magnitude closes if open exists
    if r"\left\Vert" in s:
        s = re.sub(r'\\+right\|\\+right\|', r'\\right\\Vert ', s)
        s = re.sub(r'\\+right\|', r'\\right\\Vert ', s)
        s = re.sub(r'\\+right\\\|', r'\\right\\Vert ', s)
    
    # Handle direct || notation if it looks like magnitude
    s = s.replace(r"||c\cdot \vec v||", r"\left\Vert c\cdot \vec v \right\Vert")
    s = s.replace(r"||\vec v||", r"\left\Vert \vec v \right\Vert")
    
    # 2. Fix snowflake encoding
    s = s.replace("Ôÿâ", "☃")
    s = s.replace("\\u2603", "☃")
    
    return s

def recursive_fix(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k == 'itemData' and isinstance(v, str):
                new_obj[k] = solve_latex(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    elif isinstance(obj, str):
        return solve_latex(obj)
    else:
        return obj

# Find the IDs first
query = {
    "$or": [
        {"question.content": {"$regex": r"\\left\|\\left\||\|\|\\vec|Ôÿâ"}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"\\left\|\\left\||\|\|\\vec|Ôÿâ"}},
        {"hints.content": {"$regex": r"\\left\|\\left\||\|\|\\vec|Ôÿâ"}}
    ]
}

coll = db['scraped_questions']
cursor = coll.find(query)
total = coll.count_documents(query)
print(f"Applying robust fix to {total} items in scraped_questions...")

processed = 0
for item in cursor:
    try:
        fixed_item = recursive_fix(item)
        coll.replace_one({"_id": item["_id"]}, fixed_item)
        processed += 1
        if processed % 50 == 0:
            print(f"Processed {processed}/{total}...")
    except Exception as e:
        print(f"Error processing {item['_id']}: {e}")

print(f"GLOBAL FIX COMPLETE. Updated {processed} questions.")
