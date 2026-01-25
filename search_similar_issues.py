import os
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

patterns = [
    r"\\left\|\\left\|",
    r"\\left\| \\left\|",
    r"\|\|",
    r"Ôÿâ",
    r"\\right\||",
    r"\\right\|\\|"
]

collections = ['scraped_questions', 'questions', 'dash_questions']
results = {}

print("Searching for similar issues...")

for coll_name in collections:
    coll = db[coll_name]
    count = 0
    problematic_ids = []
    
    # We'll do a simple regex search on the content field first
    # This is a broad search
    cursor = coll.find({
        "$or": [
            {"question.content": {"$regex": "|".join(patterns)}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "|".join(patterns)}}
        ]
    }, {"_id": 1})
    
    for doc in cursor:
        problematic_ids.append(str(doc['_id']))
        count += 1
        
    results[coll_name] = {
        "count": count,
        "ids": problematic_ids
    }
    print(f"Found {count} potential issues in {coll_name}")

if any(res['count'] > 0 for res in results.values()):
    print("\nProblematic IDs found:")
    for coll, res in results.items():
        if res['count'] > 0:
            print(f"{coll}: {res['ids'][:10]}{'...' if res['count'] > 10 else ''}")
else:
    print("No other problematic questions found with these patterns.")
