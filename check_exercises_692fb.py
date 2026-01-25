import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

SEARCH_TEXT = "Mediterranean forests"

print(f"Checking 'exercises' collection for '{SEARCH_TEXT}'...")
coll = db['exercises']
try:
    cursor = coll.find({
        "$or": [
            {"question.content": {"$regex": SEARCH_TEXT}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_TEXT}}
        ]
    })
    
    count = 0
    for doc in cursor:
        count += 1
        doc_str = json.dumps(doc, default=str)
        bold_count = doc_str.count("**")
        print(f"  [FOUND] Doc ID: {doc['_id']} | Bold Count: {bold_count}")
    
    if count == 0:
        print("  No matches found in 'exercises'.")
        
except Exception as e:
    print(f"  Error: {e}")
