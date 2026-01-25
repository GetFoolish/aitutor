import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

print("Searching for ALL additions with 189,360 and 22,857...")

found_ids = []
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        # Search for both numbers in any field
        cursor = coll.find({
            "$and": [
                {"$or": [
                    {"question.content": {"$regex": "189,360"}},
                    {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "189,360"}}
                ]},
                {"$or": [
                    {"question.content": {"$regex": "22,857"}},
                    {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "22,857"}}
                ]}
            ]
        })
        for doc in cursor:
            found_ids.append((coll_name, str(doc['_id'])))
    except:
        pass

print(f"\nFinal list of related IDs: {len(found_ids)}")
for c, qid in found_ids:
    print(f"- [{c}] {qid}")
