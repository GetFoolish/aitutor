
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def search_properly():
    old_hash = "c6f6211941d057c2f845d5230fbbcfc12f69be70"
    
    # 1. Search by exact hash in the 3 known image widget slots (image 1, image 2, etc.)
    # Since we don't know the slot number exactly for variants, we use an $or
    query = {"$or": [
        {"question.widgets.image 1.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 2.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 3.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 4.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 5.options.backgroundImage.url": {"$regex": old_hash}}
    ]}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Variants found by hash in explicit paths: {len(docs)}")
    for d in docs:
        print(f" - {d['_id']} | Content: {d.get('question', {}).get('content')}")

    # 2. Search by unique alt text snippet
    snippet = "negative eight, three to negative seven"
    query_alt = {"$or": [
        {"question.widgets.image 1.options.alt": {"$regex": snippet}},
        {"question.widgets.image 2.options.alt": {"$regex": snippet}},
        {"question.widgets.image 3.options.alt": {"$regex": snippet}}
    ]}
    docs_alt = list(mongo_db.scraped_questions.find(query_alt))
    print(f"\nVariants found by alt text snippet: {len(docs_alt)}")
    for d in docs_alt:
        print(f" - {d['_id']}")

    # 3. Search for function k questions generally if nothing found
    if len(docs) == 0:
        print("\nGeneric search for function k questions...")
        query_k = {"question.content": {"$regex": r"k\(.*\)"}}
        docs_k = list(mongo_db.scraped_questions.find(query_k).limit(20))
        for d in docs_k:
             print(f" - {d['_id']} | {d.get('question', {}).get('content')}")

if __name__ == "__main__":
    search_properly()
