import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

TARGET_QUESTION_ID = "20.1.1.1.7_x47f2b6253514fbda"

print(f"Searching for all docs with questionId: {TARGET_QUESTION_ID}...")

found_ids = []
for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    try:
        cursor = coll.find({"questionId": TARGET_QUESTION_ID})
        for doc in cursor:
            content = doc.get('question', {}).get('content', '')
            if not content:
                item_data_str = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '{}')
                item_data = json.loads(item_data_str)
                content = item_data.get('question', {}).get('content', '')
            
            has_pipe = "|x|" in content
            print(f"  [ID: {doc['_id']}] in {coll_name} | Has '|x|'? {has_pipe}")
            if not has_pipe:
                 print(f"    -> Malformed Content: {repr(content[:100])}")
            found_ids.append(str(doc['_id']))
    except Exception as e:
        print(f"Error in {coll_name}: {e}")

print(f"\nTotal versions found: {len(found_ids)}")
