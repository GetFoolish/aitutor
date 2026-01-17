
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_other_fruits():
    # List of fruits to check
    fruits = ['apple', 'orange', 'pear', 'grape', 'lemon', 'cherry', 'strawberry', 'melon', 'pineapple', 'watermelon']
    
    # Construct regex query
    # We want to find questions where ANY image widget text contains any of these
    
    regex_pattern = "|".join(fruits)
    print(f"Searching for regex: {regex_pattern}")
    
    query = {
        "$or": [
            {"question.widgets.image 1.options.alt": {"$regex": regex_pattern, "$options": "i"}},
            {"question.widgets.image 2.options.alt": {"$regex": regex_pattern, "$options": "i"}},
            {"question.widgets.image 3.options.alt": {"$regex": regex_pattern, "$options": "i"}},
             {"question.widgets.image 4.options.alt": {"$regex": regex_pattern, "$options": "i"}}
        ]
    }
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions with other fruits.")
    
    # Analyze which fruits were found
    found_fruits = set()
    for doc in results[:20]:
         widgets = doc.get('question', {}).get('widgets', {})
         for w_name, w_data in widgets.items():
            if w_data.get('type') == 'image':
                 alt = w_data.get('options', {}).get('alt', '').lower()
                 for f in fruits:
                     if f in alt:
                         found_fruits.add(f)
                         print(f"Found {f} in {doc['_id']}: {alt}")

    print(f"\nSummary of fruits found: {sorted(list(found_fruits))}")

if __name__ == "__main__":
    find_other_fruits()
