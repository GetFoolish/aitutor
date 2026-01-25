import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

MONGO_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME') or 'ai_tutor'

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

question_id = "693199158189149cdbee41a8"

collections_to_search = [
    'questions',
    'dash_questions',
    'generated_questions',
    'perseus_questions',
    'scraped_questions',
    'exercises'
]

print(f"Global search for question {question_id}...")

found = False
for coll_name in collections_to_search:
    print(f"Checking {coll_name}...")
    collection = db[coll_name]
    
    # Try ObjectId first
    item = None
    try:
        item = collection.find_one({"_id": ObjectId(question_id)})
    except:
        pass
        
    if not item:
        # Try as string
        item = collection.find_one({"_id": question_id})
        
    if not item:
        # Try searching by matching ID in other fields if it exists
        item = collection.find_one({"id": question_id})

    if item:
        print(f"Found question in {coll_name}!")
        item['_id'] = str(item['_id'])
        with open('target_question.json', 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        print("Saved to target_question.json")
        found = True
        break

if not found:
    print("Question not found anywhere in DB.")
