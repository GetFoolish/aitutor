
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def identify_693396fb():
    snippet = "693396fb" # Part of the filename usually matches a QID prefix or ID
    # Search for this ID or prefix
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId("693396fb20538a6f3167f7bb")})
    if doc:
        widgets = doc.get('question', {}).get('widgets', {})
        for name, data in widgets.items():
            if data.get('type') == 'image':
                print(f"ALT: {data.get('options', {}).get('alt')}")
                print(f"URL: {data.get('options', {}).get('backgroundImage', {}).get('url')}")

if __name__ == "__main__":
    identify_693396fb()
