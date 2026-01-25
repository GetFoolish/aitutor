import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

ids_to_check = ['69384abbd5f915e3ae100724', '69384aded5f915e3ae100729']

for q_id in ids_to_check:
    print(f"--- ID: {q_id} ---")
    # Try multiple collections
    item = None
    for coll_name in ['questions', 'scraped_questions']:
        item = db[coll_name].find_one({"_id": ObjectId(q_id)}) or db[coll_name].find_one({"_id": q_id})
        if item:
            print(f"Found in {coll_name}")
            break
            
    if item:
        content = item.get('question', {}).get('content', '')
        print(f"Content: {repr(content)}")
        
        # Check for magnitude or broken delimiters
        patterns = [r"||", r"left|", r"right|", r"Vert"]
        for p in patterns:
            if p in content:
                print(f"Detected pattern '{p}' in content.")
        
        try:
            item_data = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if item_data:
                # Find magnitude-like strings in itemData
                magnitude_matches = [m.start() for m in (re.finditer(r'\|\||left\|', item_data))] if 're' in locals() else []
                if magnitude_matches:
                    print(f"Detected patterns in itemData at {magnitude_matches}")
        except:
            pass
    else:
        print("Not found in any collection.")
    print("-" * 20)
