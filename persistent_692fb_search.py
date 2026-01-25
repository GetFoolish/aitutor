import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
# Ultra long timeout
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=120000, connectTimeoutMS=120000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "692fb4ae7e334152c5f474dd"

print(f"Searching for {question_id} in ALL collections...")

colls = db.list_collection_names()
found_locations = []

for c in colls:
    print(f"  Checking {c}...")
    try:
        coll = db[c]
        # Try both ID formats
        item = coll.find_one({"_id": ObjectId(question_id)})
        if not item:
            item = coll.find_one({"_id": question_id})
        
        if not item:
            # Try itemID
            item = coll.find_one({"itemId": "x8ac6cf3687599328"})
            
        if item:
             print(f"  [FOUND] in {c}! ID={item['_id']}")
             found_locations.append((c, item))
    except Exception as e:
        print(f"  Error in {c}: {e}")

if not found_locations:
    print("Not found anywhere.")
else:
    for c, item in found_locations:
        doc_str = json.dumps(item, default=str)
        if "**" in doc_str:
            print(f"  !! Still contains ** in {c}")
            idx = doc_str.find("**")
            print(f"  Snippet: {repr(doc_str[max(0, idx-20):idx+60])}")
        else:
            print(f"  Clean of ** in {c}")
