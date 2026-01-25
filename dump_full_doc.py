import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "692fb4ae7e334152c5f474dd"

print(f"Dumping doc {question_id}...")

coll = db['scraped_questions']
item = coll.find_one({"_id": ObjectId(question_id)}) or coll.find_one({"_id": question_id})

if item:
    with open('full_doc_debug.json', 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=2, ensure_ascii=False, default=str)
    print("Saved to full_doc_debug.json")
else:
    print("Not found.")
