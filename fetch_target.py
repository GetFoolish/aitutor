import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

MONGO_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME') or 'ai_tutor'
COLLECTION_NAME = 'questions'

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

question_id = "693199158189149cdbee41a8"

print(f"Searching for question {question_id} in {COLLECTION_NAME}...")

# Try both string and ObjectId
item = collection.find_one({"_id": ObjectId(question_id)})
if not item:
    item = collection.find_one({"_id": question_id})

if item:
    print("Found question!")
    # Convert ObjectId to string for JSON serialization
    item['_id'] = str(item['_id'])
    
    content = item.get('question', {}).get('content', '')
    print("Content:")
    print(content)
    
    # Save to file for easy editing
    with open('target_question.json', 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=2, ensure_ascii=False)
    print("\nSaved to target_question.json")
else:
    print("Question not found in DB.")
