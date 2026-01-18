
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def check_alt_texts():
    snippet = "ratios for angle measures"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Total variants: {len(docs)}")
    
    alts = set()
    for doc in docs:
        widgets = doc.get('question', {}).get('widgets', {})
        for name, data in widgets.items():
            if data.get('type') == 'image':
                alt = data.get('options', {}).get('alt', '')
                alts.add(alt)
    
    print("\nUnique Alt Texts found:")
    for a in sorted(list(alts)):
        print(f"- {a}")

if __name__ == "__main__":
    check_alt_texts()
