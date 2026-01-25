import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Broad keywords
KEYWORDS = ["Mediterranean forests", "woodlands, and scrub biome"]

print(f"Broad search for keywords: {KEYWORDS}...")

for coll_name in ['questions', 'scraped_questions', 'dash_questions', 'perseus_questions']:
    coll = db[coll_name]
    print(f"  Checking {coll_name}...")
    try:
        # Search for either keyword
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": "Mediterranean forests"}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "Mediterranean forests"}}
            ]
        })
        
        for doc in cursor:
            doc_str = json.dumps(doc, default=str)
            bold_count = doc_str.count("**")
            print(f"  [FOUND] Doc ID: {doc['_id']} | Bold Count: {bold_count}")
            if bold_count > 0:
                print(f"    Snippet: {repr(doc_str[doc_str.find('**')-10:doc_str.find('**')+50])}")
    except Exception as e:
        print(f"    Error in {coll_name}: {e}")

print("\nBroad search complete.")
