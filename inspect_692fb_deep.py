import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=30000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "692fb4ae7e334152c5f474dd"

print(f"Deep inspection for question {question_id}...")

for coll_name in db.list_collection_names():
    coll = db[coll_name]
    item = coll.find_one({"_id": ObjectId(question_id)}) or coll.find_one({"_id": question_id})
    if item:
        print(f"\n--- Found in collection: {coll_name} ---")
        
        # Check standard fields
        if 'question' in item:
            print(f"Content: {repr(item['question'].get('content', ''))}")
            if '**' in item['question'].get('content', ''):
                print("  !! Detected ** in question.content")
        
        # Check assessmentData
        if 'assessmentData' in item:
            try:
                item_data_str = item['assessmentData'].get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
                if item_data_str:
                    if '**' in item_data_str:
                        print("  !! Detected ** in assessmentData.itemData string")
                        # Show snippet
                        idx = item_data_str.find("**")
                        print(f"  Snippet: {repr(item_data_str[max(0, idx-20):idx+50])}")
            except:
                pass

        # Check hints
        hints = item.get('hints', [])
        for i, h in enumerate(hints):
            if '**' in h.get('content', ''):
                print(f"  !! Detected ** in hint {i}")
