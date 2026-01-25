import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "693199158189149cdbee41a8"

def dump_hex(s):
    if not s: return ""
    return ' '.join(f"{ord(c):04x}" for c in s)

with open('precise_dump.txt', 'w', encoding='utf-8') as f:
    for coll_name in ['questions', 'dash_questions', 'scraped_questions']:
        coll = db[coll_name]
        item = coll.find_one({"_id": ObjectId(question_id)})
        if not item:
            item = coll.find_one({"_id": question_id})
        
        if item:
            f.write(f"=== COLLECTION: {coll_name} ===\n")
            content = item.get('question', {}).get('content', '')
            f.write(f"CONTENT REPR: {repr(content)}\n")
            f.write(f"CONTENT HEX: {dump_hex(content)}\n\n")
            
            try:
                item_data = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
                if item_data:
                    f.write(f"ITEMDATA REPR (first 1000): {repr(item_data[:1000])}\n")
                    idx = item_data.find("left")
                    if idx != -1:
                        snippet = item_data[max(0, idx-10):idx+100]
                        f.write(f"ITEMDATA SNIPPET AROUND 'left': {repr(snippet)}\n")
                        f.write(f"ITEMDATA SNIPPET HEX: {dump_hex(snippet)}\n")
            except:
                pass
            f.write("\n" + "="*50 + "\n\n")

print("Dumped to precise_dump.txt")
