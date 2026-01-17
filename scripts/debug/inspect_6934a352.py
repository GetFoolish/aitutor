
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_6934a352():
    qid = "6934a35283a352bc91b80e48"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(content[:200])
    print("--- CONTENT END ---")
    
    widgets = doc.get('question', {}).get('widgets', {})
    print("\n--- WIDGETS ---")
    for widget_name, widget_data in widgets.items():
        widget_type = widget_data.get('type')
        print(f"{widget_name}: {widget_type}")
        if widget_type == 'image':
            img_opt = widget_data.get('options', {})
            url = img_opt.get('backgroundImage', {}).get('url', '')
            alt = img_opt.get('alt', '')
            print(f"  URL: {url}")
            print(f"  Alt: {alt}")

    # Find variants
    snippet = content[:50]
    escaped_snippet = re.escape(snippet)
    print(f"\nSearching for variants with snippet: {snippet}")
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
    print(f"Found {len(variants)} variants.")
    for v in variants:
        v_qid = v['_id']
        print(f"ID: {v_qid}")

if __name__ == "__main__":
    inspect_6934a352()
