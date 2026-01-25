import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

target_ids = [
    "692fb4ae7e334152c5f474dd", "693010ffebf6442f98aa9761", "6930288a046cc6e7b0047c71",
    "6930763473cb28d3e4ce429b", "69311a1be85464acc62b5424", "693146fb13b91b1a23d2b47e",
    "69318c05a58955192117193e", "6931def67be5c6b2e29cc926", "693215b233f9a4d79a006533",
    "69324cd02e5f91c2481807ba", "693285621a6b9ad706c7daa6", "6932b744cf05997b77546db0",
    "69335eaa46bd2cf873ae9da5", "693407fc928d27211812264b", "6934c70e64942dd77a1123f6",
    "693539ece61eddfd0c726626", "693573102a2c00b355a230e1", "6935ac4a541cdb343633e03a",
    "6935e54235efbaf0a785d2a5", "69365f9535282d2b128d1e63", "693699115ec39674620d0112"
]

print("Verifying the 21 known IDs...")
coll = db['scraped_questions']

still_dirty = []
for q_id in target_ids:
    item = coll.find_one({"_id": ObjectId(q_id)}) or coll.find_one({"_id": q_id})
    if item:
        doc_str = json.dumps(item, default=str)
        if "**" in doc_str:
            still_dirty.append(q_id)
    else:
        print(f"  Warning: {q_id} not found in scraped_questions")

print(f"Verified all 21. {len(still_dirty)} still dirty.")
if still_dirty:
    print(f"Dirty IDs: {still_dirty}")

# Now scan for ANY doc that has the Troodos text and **
print("\nScanning for ANY doc with climate text AND ** marks...")
SEARCH_TEXT = "Troodos National Forest Park"

found_untracked = []
for c_name in db.list_collection_names():
    c = db[c_name]
    try:
        # Broad lookup
        cursor = c.find({
            "$or": [
                {"question.content": {"$regex": SEARCH_TEXT}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_TEXT}}
            ]
        })
        for doc in cursor:
            if "**" in json.dumps(doc, default=str):
                found_untracked.append((c_name, str(doc['_id'])))
    except:
        pass

print(f"Found {len(found_untracked)} untracked dirty documents.")
for c, q_id in found_untracked:
    print(f"  [{c}] {q_id}")
