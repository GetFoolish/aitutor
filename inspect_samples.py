import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

ids_to_check = ['69384abbd5f915e3ae100724', '69384ac1d5f915e3ae100725', '69384ac67470c33c458e8ef0']

for q_id in ids_to_check:
    print(f"--- ID: {q_id} ---")
    item = db['questions'].find_one({"_id": ObjectId(q_id)}) or db['questions'].find_one({"_id": q_id})
    if item:
        content = item.get('question', {}).get('content', '')
        print(f"Content snippet: {content[:200]}...")
        # Check for magnitude or broken delimiters
        if "||" in content or "left|" in content:
            print("Detected pattern in content.")
        
        try:
            item_data = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if item_data and ("||" in item_data or "left|" in item_data):
                print("Detected pattern in itemData.")
        except:
            pass
    print("-" * 20)
