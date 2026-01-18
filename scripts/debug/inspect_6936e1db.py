
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_6936e1db():
    qid = "6936e1db7b73663f0e775314"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    print(f"--- Question {qid} ---")
    widgets = doc.get('question', {}).get('widgets', {})
    for name, data in widgets.items():
        if data.get('type') == 'image':
            print(f"Widget '{name}':")
            print(f"  URL: {data.get('options', {}).get('backgroundImage', {}).get('url')}")
            print(f"  ALT: {data.get('options', {}).get('alt')}")
        elif data.get('type') == 'radio':
            print(f"Widget '{name}':")
            choices = data.get('options', {}).get('choices', [])
            for i, choice in enumerate(choices):
                print(f"  Choice {i} content snippet: {choice.get('content')[:100]}...")

if __name__ == "__main__":
    inspect_6936e1db()
