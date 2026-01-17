
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_banana_images():
    # Regex for banana in case insensitive
    query = {
        "$or": [
            {"question.widgets.image 1.options.alt": {"$regex": "banana", "$options": "i"}},
            {"question.widgets.image 2.options.alt": {"$regex": "banana", "$options": "i"}},
            {"question.widgets.image 3.options.alt": {"$regex": "banana", "$options": "i"}}
        ]
    }
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions with 'banana' images.")
    
    for doc in results[:10]: # Print first 10
        print(f"ID: {doc['_id']}")
        # print alt text
        widgets = doc.get('question', {}).get('widgets', {})
        for w_name, w_data in widgets.items():
            if w_data.get('type') == 'image':
                 print(f"  {w_name} Alt: {w_data.get('options', {}).get('alt')}")

if __name__ == "__main__":
    find_banana_images()
