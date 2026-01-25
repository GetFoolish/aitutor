import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

BROKEN_URL_PART = "eef3b98b747a72ed553620be279df1c46e7eb201"
FIXED_IMAGE_URL = "/fixed_graphs/graph_69362.png"

def fix_graph_url(text):
    if not isinstance(text, str):
        return text
    # Pattern: web+graphie://cdn.kastatic.org/ka-perseus-graphie/eef3b98b...
    # We replace it with /fixed_graphs/graph_69362.png
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
            elif isinstance(v, str):
                new_obj[k] = fix_graph_url(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    else:
        return obj

print(f"Starting GLOBAL broken PPC graph fix...")

total_updated = 0
for coll_name in ['scraped_questions']:
    coll = db[coll_name]
    print(f"Processing {coll_name}...")
    try:
        cursor = coll.find({
            "$or": [
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": BROKEN_URL_PART}},
                {"question.widgets.image 1.options.backgroundImage.url": {"$regex": BROKEN_URL_PART}}
            ]
        })
        
        for doc in cursor:
            fixed_doc = recursive_fix(doc)
            coll.replace_one({"_id": doc["_id"]}, fixed_doc)
            total_updated += 1
            print(f"  Fixed ID: {doc['_id']}")
    except Exception as e:
        print(f"  Error in {coll_name}: {e}")

print(f"\nDONE. Total graphs definitively fixed: {total_updated}")
