
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_image_69360b81():
    qid = "69360b810aabe66864660c1a"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    widgets = doc.get('question', {}).get('widgets', {})
    print("--- IMAGE WIDGET ---")
    image_widget = widgets.get('image 1', {})
    print(image_widget)

if __name__ == "__main__":
    inspect_image_69360b81()
