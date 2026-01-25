import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "693199158189149cdbee41a8"

for coll_name in ['questions', 'dash_questions', 'scraped_questions']:
    coll = db[coll_name]
    item = coll.find_one({"_id": ObjectId(question_id)})
    if not item:
        item = coll.find_one({"_id": question_id})
    
    if item:
        print(f"--- {coll_name} ---")
        try:
            item_data_str = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if item_data_str:
                print(f"ItemData length: {len(item_data_str)}")
                # Find the magnitude string in the big JSON blob
                index = item_data_str.find("left")
                if index != -1:
                    print(f"Snippet around 'left': {repr(item_data_str[max(0, index-10):index+50])}")
            else:
                print("No itemData found in assessmentData.")
        except Exception as e:
            print(f"Error accessing itemData: {e}")
