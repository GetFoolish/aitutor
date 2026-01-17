
import os
import sys
import json
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_radio_choices():
    qid = "6934a35283a352bc91b80e48"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print(f"Question {qid} not found.")
        return

    widgets = doc.get('question', {}).get('widgets', {})
    if 'radio 1' in widgets:
        radio = widgets['radio 1']
        choices = radio.get('options', {}).get('choices', [])
        print(f"Found {len(choices)} choices in radio 1:")
        for i, choice in enumerate(choices):
            print(f"\n--- Choice {i+1} ---")
            content = choice.get('content', '')
            print(f"Content: {content[:100]}")
            if 'image 1' in content or '☃ image' in content:
                print("  -> Contains image widget reference")

if __name__ == "__main__":
    inspect_radio_choices()
