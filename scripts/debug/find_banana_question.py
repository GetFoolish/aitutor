
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_banana_question():
    qid = "69330417d8006a4430ca39c0"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT ---")
    print(content[:500])
    
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
            # sometimes images are in radios
            print("  (Radio content skipped for brevity)")

if __name__ == "__main__":
    inspect_banana_question()
