import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000, connectTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Unique snippet from the image
LATEX_PATTERN = r"189,360"

print(f"Searching for LaTeX content matching: {repr(LATEX_PATTERN)}...")

for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    print(f"Checking {coll_name}...")
    coll = db[coll_name]
    try:
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": LATEX_PATTERN}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": LATEX_PATTERN}}
            ]
        })
        
        for doc in cursor:
            print(f"  [FOUND] ID: {doc['_id']} in {coll_name}")
            # If found, check if it's the right one
            content = doc.get('question', {}).get('content', '')
            if not content:
                # check itemData
                content = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            
            if "22,857" in str(content):
                print(f"    -> Matches addition problem! ID: {doc['_id']}")
                with open(f"question_{doc['_id']}.json", 'w', encoding='utf-8') as f:
                     json.dump(doc, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"    Error in {coll_name}: {e}")

print("Search complete.")
