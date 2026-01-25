import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import re

load_dotenv('.env')
# Very long timeout
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000, connectTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def count_doubles(text):
    if not text or not isinstance(text, str):
        return 0
    return text.count("**")

results = []
print("Scanning collections (RETRY with longer timeout)...")

for coll_name in ['questions', 'scraped_questions']:
    print(f"Checking {coll_name}...")
    coll = db[coll_name]
    try:
        # Use projection to only get necessary fields
        cursor = coll.find(
            {"$or": [
                {"question.content": {"$regex": "\\*\\*"}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": "\\*\\*"}}
            ]},
            {
                "question.content": 1,
                "assessmentData.data.assessmentItem.item.itemData": 1,
                "_id": 1
            }
        ).batch_size(100) # Smaller batches
        
        for doc in cursor:
            content = doc.get('question', {}).get('content', '')
            item_data = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            
            c_count = count_doubles(content)
            i_count = count_doubles(item_data)
            
            total = c_count + i_count
            if total > 20: # Higher threshold for "buggy" density
                results.append({
                    "id": str(doc['_id']),
                    "collection": coll_name,
                    "count": total,
                    "preview": content[:100] if content else ""
                })
        print(f"  Finished {coll_name}")
    except Exception as e:
        print(f"  Error in {coll_name}: {e}")

# Sort by count descending
results.sort(key=lambda x: x['count'], reverse=True)

print(f"\nFound {len(results)} questions with VERY high bold count (>20).")
for r in results[:20]:
    print(f"- {r['id']} ({r['collection']}): {r['count']} marks")

with open('high_bold_report_v2.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
