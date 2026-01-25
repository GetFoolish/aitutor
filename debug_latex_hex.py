import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "693199158189149cdbee41a8"

for coll_name in ['questions', 'dash_questions', 'scraped_questions']:
    coll = db[coll_name]
    item = coll.find_one({"_id": ObjectId(question_id)})
    if not item:
        item = coll.find_one({"_id": question_id})
    
    if item:
        print(f"--- {coll_name} ---")
        content = item.get('question', {}).get('content', '')
        print(f"Content (repr): {repr(content)}")
        
        # Check perseusItem too
        p_content = item.get('perseusItem', {}).get('question', {}).get('content', '')
        print(f"Perseus Content (repr): {repr(p_content)}")
        
        # Check hints
        hints = item.get('hints', [])
        for i, h in enumerate(hints):
            print(f"Hint {i} (repr): {repr(h.get('content', ''))}")
