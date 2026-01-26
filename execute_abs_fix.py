import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def fix_absolute_value(text):
    if not isinstance(text, str):
        return text
    
    # Replace |x| with |x| (standard)
    # Actually, let's just ensure it HAS the closing pipe if it's f(x)=|x
    # But to follow "Image 2" style, let's use explicit spacing or lvert
    
    # 1. Fix the specific f(x)=|x case if it's actually missing in some docs
    # (Though my scan said it was there, maybe some itemData nested strings are different)
    
    # 2. Convert |...| to \lvert ... \rvert for robustness
    # We look for pairs of | inside mathematical contexts
    # Since these are math questions, we can be relatively aggressive
    
    # Pattern: | followed by something not | followed by |
    # But avoid matching tables.
    
    # Let's target the specific common patterns first
    text = text.replace("f(x)&=|x|", r"f(x)&=\lvert x \rvert")
    text = text.replace("f(x)=|x|", r"f(x)=\lvert x \rvert")
    
    # Handle g(x) = |x+2| + 4
    text = re.sub(r"\|x\+2\|", r"\\lvert x+2 \\rvert", text)
    text = re.sub(r"\|x\-2\|", r"\\lvert x-2 \\rvert", text)
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

print("Starting DEFINITIVE absolute value fix (|x| -> \lvert x \rvert)...")

# Search for any doc containing |x| or absolute value functions
cursor = collection.find({
    "$or": [
        {"question.content": {"$regex": r"\|x"}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"\|x"}}
    ]
})

total_updated = 0
for doc in cursor:
    fixed_doc = recursive_fix(doc)
    # Check if anything changed
    if json.dumps(fixed_doc) != json.dumps(doc):
        collection.replace_one({"_id": doc["_id"]}, fixed_doc)
        total_updated += 1
        if total_updated % 50 == 0:
            print(f"  Fixed {total_updated} docs...")

print(f"\nDONE. Total absolute value questions fixed: {total_updated}")
