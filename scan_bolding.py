import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=30000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def count_doubles(text):
    if not text or not isinstance(text, str):
        return 0
    return text.count("**")

results = []

print("Scanning all collections for high-density bolding...")

for coll_name in ['questions', 'scraped_questions', 'dash_questions']:
    coll = db[coll_name]
    # We look for documents that contain **
    cursor = coll.find({"$or": [
        {"question.content": {"$regex": "\\*\\*"}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "\\*\\*"}}
    ]})
    
    for doc in cursor:
        content = doc.get('question', {}).get('content', '')
        item_data = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
        
        c_count = count_doubles(content)
        i_count = count_doubles(item_data)
        
        total = c_count + i_count
        if total > 10: # Focus on high density first
            results.append({
                "id": str(doc['_id']),
                "collection": coll_name,
                "count": total,
                "preview": content[:100] + "..."
            })

# Sort by count descending
results.sort(key=lambda x: x['count'], reverse=True)

print(f"\nFound {len(results)} questions with high bold count (>10).")
for r in results[:15]:
    print(f"- {r['id']} ({r['collection']}): {r['count']} marks | {r['preview']}")

with open('high_bold_report.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
