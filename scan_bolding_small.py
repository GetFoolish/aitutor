import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
# Direct connection if possible or just very long timeout
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def count_doubles(text):
    if not text or not isinstance(text, str):
        return 0
    return text.count("**")

results = []
print("Scanning SMALL 'questions' collection...")

try:
    coll = db['questions']
    # Small limit to ensure we get something before a timeout
    cursor = coll.find({"$or": [
        {"question.content": {"$regex": "\\*\\*"}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "\\*\\*"}}
    ]}).limit(2000)
    
    for doc in cursor:
        content = doc.get('question', {}).get('content', '')
        item_data = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
        
        count = count_doubles(content) + count_doubles(item_data)
        if count > 10:
            results.append({
                "id": str(doc['_id']),
                "count": count,
                "preview": content[:100] if content else ""
            })

    results.sort(key=lambda x: x['count'], reverse=True)
    print(f"Found {len(results)} high-bold questions in 'questions' collection.")
    for r in results[:10]:
         print(f"- {r['id']}: {r['count']} marks | {r['preview']}")

except Exception as e:
    print(f"Error: {e}")

with open('small_bold_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
