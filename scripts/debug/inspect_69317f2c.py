
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_69317f2c():
    qid = "69317f2c47a2cb48fc68c308"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(content)
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
        elif widget_type == 'radio':
            choices = widget_data.get('options', {}).get('choices', [])
            for i, choice in enumerate(choices):
                print(f"  Choice {i}: {choice.get('content', '')[:100]}...")

    # Find variants
    # Use a distinctive snippet from the content to find variants
    snippet = content[:50]
    # Escape special regex chars
    escaped_snippet = re.escape(snippet)
    
    print(f"\nSearching for variants with snippet: {snippet}")
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
    print(f"Found {len(variants)} variants.")
    for v in variants:
        v_qid = v['_id']
        print(f"ID: {v_qid}")

if __name__ == "__main__":
    inspect_69317f2c()
