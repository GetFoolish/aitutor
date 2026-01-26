import os
import json
import re
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Corrected regex to find f(x)=|x without closing |
# Note: In Mongo $regex we need to escape | as \|
FIND_PATTERN = r"f\(x\)&=\|x(?!\||\\)"

print(f"Searching for questions with REAL missing pipes...")

found_ids = []
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": FIND_PATTERN}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": FIND_PATTERN}}
            ]
        })
        
        for doc in cursor:
            content = doc.get('question', {}).get('content', '')
            if not content:
                item_data_str = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '{}')
                item_data = json.loads(item_data_str)
                content = item_data.get('question', {}).get('content', '')
            
            # Additional python check to be sure
            if re.search(r"f\(x\)&=\|x(?!\|)", content):
                print(f"  [REAL BROKEN] Coll: {coll_name}, ID: {doc['_id']}")
                found_ids.append((coll_name, str(doc['_id'])))
    except Exception as e:
        print(f"Error in {coll_name}: {e}")

print(f"\nDone. Found {len(found_ids)} definitively broken documents.")
