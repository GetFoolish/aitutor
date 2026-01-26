import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=120000, connectTimeoutMS=120000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def fix_absolute_value(text):
    if not isinstance(text, str):
        return text
    
    # Target f(x)=|x case even if missing closing pipe
    text = re.sub(r"f\(x\)\s*&=\s*\|x(?!\s*\|)", r"f(x)&=\\lvert x \\rvert", text)
    text = re.sub(r"f\(x\)\s*=\s*\|x(?!\s*\|)", r"f(x)=\\lvert x \\rvert", text)
    
    # 2. Standard replacements for robustness
    text = text.replace("f(x)&=|x|", r"f(x)&=\lvert x \rvert")
    text = text.replace("f(x)=|x|", r"f(x)=\lvert x \rvert")
    
    # Handle g(x) = |x+2| + 4 and similar
    text = re.sub(r"\|x\+([0-9]+)\|", r"\\lvert x+\1 \\rvert", text)
    text = re.sub(r"\|x\-([0-9]+)\|", r"\\lvert x-\1 \\rvert", text)
    text = re.sub(r"\|x\|", r"\\lvert x \\rvert", text)
    
    return text

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
                    new_obj[k] = fix_absolute_value(v)
            elif isinstance(v, str):
                new_obj[k] = fix_absolute_value(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    else:
        return obj

COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print("Starting GLOBAL absolute value fix (V2)...")

cursor = collection.find({
    "$or": [
        {"question.content": {"$regex": r"\|x"}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"\|x"}}
    ]
})

total_updated = 0
for doc in cursor:
    fixed_doc = recursive_fix(doc)
    
    # Better comparison: check only modified fields or deep compare
    # To avoid ObjectId issues in comparison:
    def mongo_json_friendly(o):
        if isinstance(o, ObjectId): return str(o)
        from datetime import datetime
        if isinstance(o, datetime): return o.isoformat()
        return o

    if json.dumps(fixed_doc, default=mongo_json_friendly) != json.dumps(doc, default=mongo_json_friendly):
        collection.replace_one({"_id": doc["_id"]}, fixed_doc)
        total_updated += 1
        if total_updated % 50 == 0:
            print(f"  Fixed {total_updated} docs...")

print(f"\nDONE. Total absolute value questions fixed: {total_updated}")
