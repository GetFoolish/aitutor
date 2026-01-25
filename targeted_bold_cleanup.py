import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=45000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

patterns = [
    r"\*\*\s+\*\*", # Redundant bold spaces
    r"\*\*\*\*",     # Empty double bold
    r"\s+\*\*",      # Bold starting with space (sometimes)
    r"\*\*\s+"       # Bold ending with space (sometimes)
]

def clean_bolding(text):
    if not isinstance(text, str):
        return text
    # Fix the most obvious errors
    text = text.replace("****", "")
    text = re.sub(r"\*\*\s+\*\*", " ", text)
    # Remove ** if it's wrapping nothing
    text = re.sub(r"\*\*\s+\*\*", "", text)
    
    return text

def recursive_fix(obj):
    if isinstance(obj, dict):
        return {k: recursive_fix(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    elif isinstance(obj, str):
        return clean_bolding(obj)
    else:
        return obj

print("Cleaning specific over-bolding patterns...")

total_fixed = 0
for coll_name in ['questions', 'scraped_questions']:
    coll = db[coll_name]
    try:
        # Search for any doc containing **** or **  **
        cursor = coll.find({"$or": [
            {"question.content": {"$regex": "\\*\\*\\s+\\*\\*|\\*\\*\\*\\*"}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "\\*\\*\\s+\\*\\*|\\*\\*\\*\\*"}}
        ]})
        
        for doc in cursor:
            fixed_doc = recursive_fix(doc)
            coll.replace_one({"_id": doc["_id"]}, fixed_doc)
            total_fixed += 1
            if total_fixed % 20 == 0:
                print(f"Fixed {total_fixed} docs...")
                
    except Exception as e:
        print(f"Error in {coll_name}: {e}")

print(f"DONE. Total questions cleaned: {total_fixed}")
