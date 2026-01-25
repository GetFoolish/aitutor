import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "69397f3b93ffc72ddaed8fb5"

coll = db['scraped_questions']
item = coll.find_one({"_id": ObjectId(question_id)})

if item:
    with open(f'question_{question_id}.json', 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=2, ensure_ascii=False, default=str)
    print("Done.")
else:
    print("Not found.")
