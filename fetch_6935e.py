import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "6935e15e35efbaf0a785d235"

for coll_name in ['questions', 'dash_questions', 'scraped_questions']:
    coll = db[coll_name]
    item = coll.find_one({"_id": ObjectId(question_id)})
    if not item:
        item = coll.find_one({"_id": question_id})
    
    if item:
        print(f"--- Found in {coll_name} ---")
        with open(f'question_{question_id}.json', 'w', encoding='utf-8') as f:
            # Custom encoder to handle ObjectId
            class MongoEncoder(json.JSONEncoder):
                def default(self, o):
                    if isinstance(o, ObjectId):
                        return str(o)
                    return super().default(o)
            json.dump(item, f, indent=2, ensure_ascii=False, cls=MongoEncoder)
        print(f"Saved to question_{question_id}.json")
