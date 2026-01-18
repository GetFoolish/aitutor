
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def search_fixed_type():
    snippet = "adjacent leg length"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} questions of this type.")
    
    hashes_to_fixed = {}
    for doc in docs:
        widgets = doc.get('question', {}).get('widgets', {})
        for name, data in widgets.items():
            if data.get('type') == 'image':
                url = data.get('options', {}).get('backgroundImage', {}).get('url', '')
                alt = data.get('options', {}).get('alt', '')
                if url.startswith('/fixed_graphs/'):
                    print(f"FIXED: {doc['_id']} uses {url}")
                    # We can't easily know the original hash here if it was already overwritten
                    # unless we find another one that is NOT fixed.
                elif url.startswith('web+graphie'):
                    # Save the hash part
                    h = url.split('/')[-1]
                    hashes_to_fixed[h] = alt

    print("\nStill broken hashes in this type:")
    for h, alt in hashes_to_fixed.items():
         print(f"- {h}: {alt[:50]}...")

if __name__ == "__main__":
    search_fixed_type()
