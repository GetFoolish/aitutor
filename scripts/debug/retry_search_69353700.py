
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def retry_search():
    prefix = "69353700"
    print(f"Searching for IDs starting with {prefix}")
    
    # Mongo search for IDs starting with prefix
    docs = list(mongo_db.scraped_questions.find({"_id": {"$regex": f"^{prefix}"}}))
    print(f"Found {len(docs)} docs with prefix")
    for d in docs:
        print(f" - {d['_id']} | Content: {d.get('question', {}).get('content')}")

    # Also search for the exact hash string anywhere in the widgets
    old_hash = "c6f6211941d057c2f845d5230fbbcfc12f69be70"
    print(f"\nSearching for exact hash string in widgets: {old_hash}")
    # Using a simpler regex that doesn't escape dots if not needed, or just $regex
    docs_hash = list(mongo_db.scraped_questions.find({"question.widgets": {"$regex": old_hash}}))
    print(f"Found {len(docs_hash)} docs with hash")
    for d in docs_hash:
        print(f" - {d['_id']}")

    # Search for "function k" in the alt text
    print("\nSearching for 'function k' in image alt text")
    docs_alt = list(mongo_db.scraped_questions.find({"question.widgets": {"$regex": "function k"}}))
    print(f"Found {len(docs_alt)} docs with 'function k' in alt")
    for d in docs_alt:
        print(f" - {d['_id']}")

if __name__ == "__main__":
    retry_search()
