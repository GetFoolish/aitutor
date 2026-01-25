import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

SEARCH_CAPTION = "Sticky leaf traps of a Venus flytrap"
SEARCH_QUESTION = "Which of the following describes a biotic factor in the Venus flytrap"

print(f"Searching for questions related to Venus flytrap...")

found_docs = []
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": SEARCH_QUESTION}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_QUESTION}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_CAPTION}}
            ]
        })
        
        for doc in cursor:
            doc_str = json.dumps(doc, default=str)
            star_count = doc_str.count("*")
            print(f"  [FOUND] Coll: {coll_name}, ID: {doc['_id']} | Stars found: {star_count}")
            found_docs.append((coll_name, str(doc['_id'])))
    except Exception as e:
        print(f"Error in {coll_name}: {e}")

print(f"\nDone. Found {len(found_docs)} related documents.")
