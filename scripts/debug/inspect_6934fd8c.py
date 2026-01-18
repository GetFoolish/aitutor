
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_6934fd8c():
    qid = "6934fd8cb93b2fcaf1995ba5"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    print(f"--- Question {qid} ---")
    print(f"Content: {doc.get('question', {}).get('content')}")
    
    widgets = doc.get('question', {}).get('widgets', {})
    radio_widget = widgets.get('radio 1', {})
    if radio_widget:
        print("\n--- Radio Widget Choices ---")
        choices = radio_widget.get('options', {}).get('choices', [])
        for i, choice in enumerate(choices):
            print(f"Choice {i}: {choice.get('content')}")

if __name__ == "__main__":
    inspect_6934fd8c()
