import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

target_ids = [
    "6934bde26a69d82b28838eba",
    "6934f79bcd4923e2c34532af",
    "6935e15e35efbaf0a785d235",
    "6936551c4d5b9546f400db9a",
    "693655204d5b9546f400db9b",
    "6936c7a7f7fb1241c0114a6f",
    "6936c7acf7fb1241c0114a70"
]

NEW_IMAGE_URL = "/fixed_graphs/graph_6935e.png"

def fix_content(data):
    if not isinstance(data, str):
        return data
        
    # Replace the specific broken graphie URLs with the new local image path
    # We target both original cdn URLs and the athena-assets.s3 proxy versions
    patterns = [
        r"web\+graphie://cdn\.kastatic\.org/ka-perseus-graphie/5af3293ab60e114001dfa57f97f9cd9a34fdb26b",
        r"web\+graphie://cdn\.kastatic\.org/ka-perseus-graphie/7bda202ee1637a7a6c2d2a2d0f26a54d59914cdb",
        r"https://athena-assets\.s3\.amazonaws\.com/ka-perseus-graphie/5af3293ab60e114001dfa57f97f9cd9a34fdb26b",
        r"https://athena-assets\.s3\.amazonaws\.com/ka-perseus-graphie/7bda202ee1637a7a6c2d2a2d0f26a54d59914cdb"
    ]
    
    for p in patterns:
        data = re.sub(p, NEW_IMAGE_URL, data)
        
    return data

def recursive_fix(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k == 'itemData' and isinstance(v, str):
                # itemData is a JSON string
                try:
                    inner_data = json.loads(v)
                    fixed_inner = recursive_fix(inner_data)
                    new_obj[k] = json.dumps(fixed_inner, ensure_ascii=False)
                except:
                    new_obj[k] = fix_content(v)
            elif k in ['url', 'backgroundImage', 'imageUrl'] and isinstance(v, (str, dict)):
                if isinstance(v, str):
                    new_obj[k] = fix_content(v)
                else:
                    new_obj[k] = recursive_fix(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    elif isinstance(obj, str):
        return fix_content(obj)
    else:
        return obj

COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print(f"Starting global graph replacement for {len(target_ids)} IDs...")

updated_count = 0
for q_id in target_ids:
    print(f"Processing {q_id}...")
    item = collection.find_one({"_id": ObjectId(q_id)}) or collection.find_one({"_id": q_id})
    if item:
        fixed_item = recursive_fix(item)
        result = collection.replace_one({"_id": item["_id"]}, fixed_item)
        if result.modified_count > 0:
            print(f"  Successfully updated.")
            updated_count += 1
        else:
            print(f"  No changes needed or update failed.")
    else:
        print(f"  Question not found.")

print(f"Finished. Total updated: {updated_count}")
