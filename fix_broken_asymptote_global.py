import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

BROKEN_URL_PART = "43e5020c68f2b1cee7aa064e7aa38b04f406630a"
FIXED_IMAGE_URL = "/fixed_graphs/graph_69374.png"

def fix_graph_url(text):
    if not isinstance(text, str):
        return text
    # Pattern: web+graphie://cdn.kastatic.org/ka-perseus-graphie/43e5020c...
    return re.sub(r"web\+graphie://cdn\.kastatic\.org/ka-perseus-graphie/" + BROKEN_URL_PART, FIXED_IMAGE_URL, text)

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
                    new_obj[k] = fix_graph_url(v)
            elif (k == url and isinstance(v, str)) or isinstance(v, str):
                new_obj[k] = fix_graph_url(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    else:
        return obj

print(f"Starting GLOBAL broken asymptote graph fix...")

# Correcting my logic in recursive_fix for images objects
def recursive_fix_v2(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            # Check the key itself for image map
            new_key = fix_graph_url(k)
            if k == 'itemData' and isinstance(v, str):
                try:
                    inner_data = json.loads(v)
                    fixed_inner = recursive_fix_v2(inner_data)
                    new_obj[new_key] = json.dumps(fixed_inner, ensure_ascii=False)
                except:
                    new_obj[new_key] = fix_graph_url(v)
            elif isinstance(v, str):
                new_obj[new_key] = fix_graph_url(v)
            else:
                new_obj[new_key] = recursive_fix_v2(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix_v2(i) for i in obj]
    else:
        return obj

total_updated = 0
for coll_name in ['scraped_questions']:
    coll = db[coll_name]
    print(f"Processing {coll_name}...")
    try:
        cursor = coll.find({
            "$or": [
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": BROKEN_URL_PART}},
                {"question.images." + BROKEN_URL_PART: {"$exists": True}}
            ]
        })
        
        for doc in cursor:
            fixed_doc = recursive_fix_v2(doc)
            coll.replace_one({"_id": doc["_id"]}, fixed_doc)
            total_updated += 1
            print(f"  Fixed ID: {doc['_id']}")
    except Exception as e:
        print(f"  Error in {coll_name}: {e}")

print(f"\nDONE. Total graphs definitively fixed: {total_updated}")
