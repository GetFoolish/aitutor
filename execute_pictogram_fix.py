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
    "69309146e3928da5187fe3c4",
    "6931556dbd78eec1e54b51af",
    "6931ce2836979a821f00f0ff",
    "69332dde42728321ec258a53",
    "6933dad245a4cb2e2ed4454a",
    "69356eab2a2c00b355a23059",
    "6935a7a9541cdb343633dfaf",
    "6935e06835efbaf0a785d21a",
    "693619a9b6dab7b3d9e776dd",
    "6936542d4d5b9546f400db83",
    "6936ff69b753254d0bf6ff2c"
]

# We need to replace several different broken graphie URLs with the one correct static image
NEW_IMAGE_URL = "/fixed_graphs/graph_6936f.png"

def fix_content(data):
    if not isinstance(data, str):
        return data
        
    # The pictogram question uses multiple different graphie URLs (hints vs question)
    # We'll use a regex to match the most common Perseus graphie patterns
    data = re.sub(r"web\+graphie://cdn\.kastatic\.org/ka-perseus-graphie/[a-f0-9]{40}", NEW_IMAGE_URL, data)
    data = re.sub(r"https://athena-assets\.s3\.amazonaws\.com/ka-perseus-graphie/[a-f0-9]{40}", NEW_IMAGE_URL, data)
    
    return data

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

print(f"Starting global pictogram replacement for {len(target_ids)} IDs...")

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
