import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=30000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

target_ids = [
    "692fb4ae7e334152c5f474dd",
    "693010ffebf6442f98aa9761",
    "6930288a046cc6e7b0047c71",
    "6930763473cb28d3e4ce429b",
    "69311a1be85464acc62b5424",
    "693146fb13b91b1a23d2b47e",
    "69318c05a58955192117193e",
    "6931def67be5c6b2e29cc926",
    "693215b233f9a4d79a006533",
    "69324cd02e5f91c2481807ba",
    "693285621a6b9ad706c7daa6",
    "6932b744cf05997b77546db0",
    "69335eaa46bd2cf873ae9da5",
    "693407fc928d27211812264b",
    "6934c70e64942dd77a1123f6",
    "693539ece61eddfd0c726626",
    "693573102a2c00b355a230e1",
    "6935ac4a541cdb343633e03a",
    "6935e54235efbaf0a785d2a5",
    "69365f9535282d2b128d1e63",
    "693699115ec39674620d0112"
]

def remove_bold(text):
    if not isinstance(text, str):
        return text
    # Remove **text** -> text
    return text.replace("**", "")

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
                    new_obj[k] = remove_bold(v)
            elif k == 'content' and isinstance(v, str):
                new_obj[k] = remove_bold(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    elif isinstance(obj, str):
        # We don't want to blindly remove ** from ALL strings (like URLs if they exist)
        # but in this context it's mostly content
        return remove_bold(obj)
    else:
        return obj

COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print(f"Removing bold markers for {len(target_ids)} IDs...")

updated_count = 0
for q_id in target_ids:
    print(f"Processing {q_id}...")
    item = collection.find_one({"_id": ObjectId(q_id)}) or collection.find_one({"_id": q_id})
    if item:
        fixed_item = recursive_fix(item)
        collection.replace_one({"_id": item["_id"]}, fixed_item)
        updated_count += 1
    else:
        print(f"  Warning: ID {q_id} not found.")

print(f"Finished. Total updated: {updated_count}")
