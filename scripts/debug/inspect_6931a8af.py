
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_6931a8af():
    qid = "6931a8af84609b1e86becd5b"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(repr(content))
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
            for idx, choice in enumerate(choices):
                choice_content = choice.get('content', '')
                print(f"  Choice {idx}: {repr(choice_content)}")

    # Find variants
    # Use a snippet from the content to find variants
    snippet = content[:50] if len(content) > 50 else content
    if snippet:
        # Escape special regex characters
        escaped_snippet = re.escape(snippet)
        print(f"\nSearching for variants with snippet: {repr(snippet)}")
        variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
        print(f"Found {len(variants)} variants.")
        for v in variants:
            print(f"ID: {v['_id']}")

if __name__ == "__main__":
    inspect_6931a8af()
