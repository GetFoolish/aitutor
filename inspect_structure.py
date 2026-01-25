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
    item = db['questions'].find_one({"_id": ObjectId(q_id)}) or db['questions'].find_one({"_id": q_id})
    if item:
        print(f"Keys: {list(item.keys())}")
        if 'question' in item:
            print(f"Question keys: {list(item['question'].keys())}")
            print(f"Question Content: {repr(item['question'].get('content'))}")
            
        if 'perseusItem' in item:
            print("Found perseusItem")
            p_q = item['perseusItem'].get('question', {})
            print(f"Perseus Content: {repr(p_q.get('content'))[:200]}...")
            
        if 'assessmentData' in item:
             print("Found assessmentData")
    else:
        print("Not found.")
    print("-" * 20)
