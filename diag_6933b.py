import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "6933bac5cd077787e27dc81b"

coll = db['scraped_questions']
item = coll.find_one({"_id": ObjectId(question_id)}) or coll.find_one({"_id": question_id})

if item:
    item_data_str = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '{}')
    item_data = json.loads(item_data_str)
    content = item_data.get('question', {}).get('content', '')
    
    print("--- RAW CONTENT START ---")
    print(content)
    print("--- RAW CONTENT END ---")
    
    # Check specifically for f(x)&=|x|
    if "f(x)&=|x|" in content:
        print("FOUND f(x)&=|x|")
    elif "f(x)&=|x" in content:
        print("FOUND f(x)&=|x without closing pipe")
else:
    print("Not found.")
