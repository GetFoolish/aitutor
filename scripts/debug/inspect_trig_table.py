import os
import sys
from pymongo import MongoClient
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_question(qid_str):
    collection = mongo_db.scraped_questions

    try:
        qid = ObjectId(qid_str)
    except:
        qid = qid_str

    question = collection.find_one({"_id": qid})
    if not question:
        print(f"Question {qid_str} not found.")
        return

    print(f"--- Question ID: {qid_str} ---")
    content = question.get('question', {}).get('content', '')
    print("Content:")
    print(content)
    
    widgets = question.get('question', {}).get('widgets', {})
    for widget_id, widget_data in widgets.items():
        print(f"\nWidget: {widget_id}")
        if 'table' in widget_id:
            print(widget_data.get('options', {}).get('headers', []))
            print(widget_data.get('options', {}).get('rows', []))
        elif 'image' in widget_id:
             print(widget_data.get('options', {}).get('backgroundImage', {}).get('url', ''))
        elif 'radio' in widget_id:
             choices = widget_data.get('options', {}).get('choices', [])
             for i, choice in enumerate(choices):
                 print(f"Choice {i}: {choice.get('content', '')}")

if __name__ == "__main__":
    inspect_question("69360b810aabe66864660c1a")
