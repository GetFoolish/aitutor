import os
import json
import re
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Search for |x| or |x followed by newline stuff
# Maybe it's |x\|? 
FIND_PATTERN = r"\|x\|[\s\S]*?\\\\"

print(f"Scanning for |x| follow-ups...")

found_ids = []
for coll_name in ['scraped_questions']:
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
             
             if "|x|" in content and ("\\\\" in content or "\n" in content):
                  print(f"  [FOUND] ID: {doc['_id']}")
                  found_ids.append(str(doc['_id']))
    except Exception as e:
        print(f"Error: {e}")

print(f"\nDone. Found {len(found_ids)}")
