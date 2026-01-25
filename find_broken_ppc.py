import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Broken background URL identifier from retrieved JSON
BROKEN_URL_PART = "eef3b98b747a72ed553620be279df1c46e7eb201"

print(f"Searching for all questions with graph ID: {BROKEN_URL_PART}...")

found_ids = []
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        # Search itemData (stringified) and question.widgets (for direct objects)
        cursor = coll.find({
            "$or": [
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": BROKEN_URL_PART}},
                {"question.widgets.image 1.options.backgroundImage.url": {"$regex": BROKEN_URL_PART}}
            ]
        })
        
        for doc in cursor:
            print(f"  [FOUND] Coll: {coll_name}, ID: {doc['_id']}")
            found_ids.append((coll_name, str(doc['_id'])))
    except Exception as e:
        print(f"Error in {coll_name}: {e}")

print(f"\nDone. Found {len(found_ids)} dirty documents.")
