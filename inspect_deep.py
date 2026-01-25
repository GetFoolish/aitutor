import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

q_id = '69384abbd5f915e3ae100724'
item = db['questions'].find_one({"_id": ObjectId(q_id)}) or db['questions'].find_one({"_id": q_id})

if item:
    print(f"--- ID: {q_id} ---")
    assessment_data = item.get('assessmentData', {})
    item_data_str = assessment_data.get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
    
    if item_data_str:
        print("Found itemData JSON string.")
        try:
            item_data = json.loads(item_data_str)
            content = item_data.get('question', {}).get('content', '')
            print(f"Inner Content: {repr(content)[:500]}...")
            
            if "||" in content or "left|" in content:
                print("Detected LaTeX magnitude pattern in inner content!")
        except Exception as e:
            print(f"Error parsing itemData JSON: {e}")
            print(f"Raw snippet: {repr(item_data_str[:200])}")
    else:
        print("No itemData string found in assessmentData.")
else:
    print("Item not found.")
