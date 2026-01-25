import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

SEARCH_QUESTION = "Which of the following describes a biotic factor in the Venus flytrap"

def remove_all_stars(text):
    if not isinstance(text, str):
        return text
    return text.replace("**", "").replace("*", "")

def recursive_fix(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k == 'itemData' and isinstance(v, str):
                try:
                    inner_data = json.loads(v)
                    fixed_inner = recursive_fix(inner_data)
                    new_obj[k] = json.dumps(fixed_inner, ensure_ascii=False)
                except:
                    new_obj[k] = remove_all_stars(v)
            elif k in ['content', 'caption', 'clue', 'explanation'] and isinstance(v, str):
                new_obj[k] = remove_all_stars(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    else:
        return obj

print("Starting Venus flytrap asterisk cleanup...")

total_updated = 0
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    print(f"Processing {coll_name}...")
    try:
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": SEARCH_QUESTION}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_QUESTION}}
            ]
        })
        
        for doc in cursor:
            fixed_doc = recursive_fix(doc)
            coll.replace_one({"_id": doc["_id"]}, fixed_doc)
            total_updated += 1
            if total_updated % 10 == 0:
                print(f"  Processed {total_updated} docs...")
    except Exception as e:
        print(f"  Error in {coll_name}: {e}")

print(f"\nDONE. Total questions definitively cleaned: {total_updated}")
