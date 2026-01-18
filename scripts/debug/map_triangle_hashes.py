
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def map_hashes():
    snippet = "ratios for angle measures"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    
    mapping = {}
    for doc in docs:
        widgets = doc.get('question', {}).get('widgets', {})
        for name, data in widgets.items():
            if data.get('type') == 'image':
                url = data.get('options', {}).get('backgroundImage', {}).get('url', '')
                alt = data.get('options', {}).get('alt', '')
                if url.startswith('web+graphie'):
                    mapping[url] = alt
                elif url.startswith('/'):
                    print(f"ALREADY FIXED: {doc['_id']} with {url} ({alt[:50]}...)")
    
    print("\nUnique Broken Hashes and their Alt Text:")
    for url, alt in mapping.items():
        print(f"- URL: {url}\n  ALT: {alt}\n")

if __name__ == "__main__":
    map_hashes()
