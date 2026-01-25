import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# target sentence
SENTENCE = "Which of the following graphs best matches the climate"

print(f"Searching for all docs related to climate matching sentence: {repr(SENTENCE)}...")

found_docs = []
for coll_name in ['questions', 'scraped_questions']:
    coll = db[coll_name]
    try:
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": SENTENCE}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SENTENCE}}
            ]
        })
        
        for doc in cursor:
            doc_str = json.dumps(doc, default=str)
            if "**" in doc_str:
                found_docs.append((coll_name, str(doc['_id'])))
                print(f"  [FOUND DIRTY] Coll: {coll_name}, ID: {doc['_id']} | Snippet: {repr(doc_str[doc_str.find('**'):doc_str.find('**')+40])}")
    except Exception as e:
         print(f"Error in {coll_name}: {e}")

print(f"\nDone. Found {len(found_docs)} dirty documents.")
