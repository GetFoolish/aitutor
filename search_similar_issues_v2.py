import os
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# More specific patterns that indicate magnitude notation problems or encoding errors
patterns = [
    r"\\left\|\\left\|",
    r"\\left\| \\left\|",
    r"\|\|\s*\\vec",   # Magnitude of a vector
    r"\|\|\s*[a-zA-Z]", # Magnitude of a variable
    r"Ôÿâ",             # Encoding error
    r"\\right\||",      # Incomplete my previous fix
    r"\\right\|\\|"     # Incomplete my previous fix
]

collections = ['questions', 'scraped_questions']
results = {}

print("Searching for TRUE similar issues...")

for coll_name in collections:
    coll = db[coll_name]
    problematic_ids = []
    
    # Using $regex with $or
    cursor = coll.find({
        "$or": [
            {"question.content": {"$regex": "|".join(patterns)}},
            {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "|".join(patterns)}},
            {"hints.content": {"$regex": "|".join(patterns)}}
        ]
    }, {"_id": 1})
    
    for doc in cursor:
        problematic_ids.append(str(doc['_id']))
        
    results[coll_name] = len(problematic_ids)
    if problematic_ids:
        print(f"Found {len(problematic_ids)} real issues in {coll_name}")
        print(f"Sample IDs: {problematic_ids[:5]}")

print("\nSummary:")
for coll, count in results.items():
    print(f"- {coll}: {count}")
