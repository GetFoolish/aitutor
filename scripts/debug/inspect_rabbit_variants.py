
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_rabbit_variants():
    snippet = "**Which image shows an even number of rabbits?**\n\n"
    escaped_snippet = re.escape(snippet)
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
    
    print(f"Found {len(variants)} variants.")
    for v in variants:
        qid = str(v['_id'])
        print(f"\n--- Question ID: {qid} ---")
        widgets = v.get('question', {}).get('widgets', {})
        for widget_name, widget_data in widgets.items():
            if widget_data.get('type') == 'radio':
                choices = widget_data.get('options', {}).get('choices', [])
                for idx, choice in enumerate(choices):
                    content = choice.get('content', '')
                    # Extract alt text from markdown image
                    match = re.search(r'!\[([^\]]*)\]', content)
                    alt = match.group(1) if match else "NO ALT"
                    print(f"  Choice {idx} Alt: {repr(alt)}")

if __name__ == "__main__":
    inspect_rabbit_variants()
