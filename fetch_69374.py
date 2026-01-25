import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "69374f43150db826a8c25657"

collections = ['questions', 'scraped_questions', 'dash_questions']

found = False
for coll_name in collections:
    print(f"Checking {coll_name}...")
    coll = db[coll_name]
    try:
        item = coll.find_one({"_id": ObjectId(question_id)}) or coll.find_one({"_id": question_id})
            
        if item:
            print(f"--- Found in {coll_name} ---")
            with open(f'question_{question_id}.json', 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=2, ensure_ascii=False, default=str)
            print(f"Saved to question_{question_id}.json")
            found = True
            break
    except Exception as e:
        print(f"Error checking {coll_name}: {e}")

if not found:
    print("Question not found anywhere in DB.")
