import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Missing pipe pattern from the retrieved JSON
SEARCH_PATTERN = r"f(x)&=|x"
SEARCH_STRICT = "f(x)&=|x\\"

print(f"Searching for questions related to missing pipe in absolute value...")

found_docs = []
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        # Search for the specific malformed LaTeX
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": r"f\(x\)&=|x(?![|])"}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"f\(x\)&=|x(?![|])"}}
            ]
        })
        
        for doc in cursor:
            content = doc.get('question', {}).get('content', '')
            if not content:
                content = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            
            print(f"  [FOUND] Coll: {coll_name}, ID: {doc['_id']}")
            found_docs.append((coll_name, str(doc['_id'])))
    except Exception as e:
        print(f"Error in {coll_name}: {e}")

print(f"\nDone. Found {len(found_docs)} related documents.")
