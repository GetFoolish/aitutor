import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client['khan_academy_test']

SEARCH_TEXT = "Mediterranean forests"

print(f"Checking 'khan_academy_test' for '{SEARCH_TEXT}'...")

for coll_name in db.list_collection_names():
    print(f"  Checking collection: {coll_name}...")
    coll = db[coll_name]
    try:
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": SEARCH_TEXT}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_TEXT}}
            ]
        })
        
        for doc in cursor:
            doc_str = json.dumps(doc, default=str)
            bold_count = doc_str.count("**")
            print(f"  [FOUND] ID: {doc['_id']} | Bold: {bold_count}")
    except Exception as e:
        print(f"    Error: {e}")

print("Search in khan_academy_test complete.")
