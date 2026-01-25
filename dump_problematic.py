import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

patterns = [
    r"\\left\|\\left\|",
    r"\\left\| \\left\|",
    r"\|\|\s*\\vec",
    r"\|\|\s*[a-zA-Z]",
    r"Ôÿâ",
    r"\\right\||",
    r"\\right\|\\|"
]

cursor = db['questions'].find({
    "$or": [
        {"question.content": {"$regex": "|".join(patterns)}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "|".join(patterns)}},
        {"hints.content": {"$regex": "|".join(patterns)}}
    ]
})

with open('problematic_questions_dump.txt', 'w', encoding='utf-8') as f:
    for item in cursor:
        f.write(f"--- ID: {item['_id']} ---\n")
        try:
            item_data_str = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if item_data_str:
                item_data = json.loads(item_data_str)
                content = item_data.get('question', {}).get('content', '')
                f.write(f"INNER CONTENT: {repr(content)}\n")
        except Exception as e:
            f.write(f"ERROR: {e}\n")
        f.write("\n" + "="*50 + "\n\n")

print("Dumped to problematic_questions_dump.txt")
