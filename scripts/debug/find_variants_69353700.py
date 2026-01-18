
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_variants_69353700():
    old_hash = "c6f6211941d057c2f845d5230fbbcfc12f69be70"
    
    # 1. Search by hash in widgets
    query_hash = {"question.widgets": {"$regex": old_hash}}
    docs_by_hash = list(mongo_db.scraped_questions.find(query_hash))
    print(f"Variants found by hash: {len(docs_by_hash)}")
    
    # 2. Search by content pattern: $k(...) = [[...]]
    # Using regex to find questions about function k
    query_content = {"question.content": {"$regex": r"\$k\(.*\)=\[\[☃ numeric-input 1\]\]"}}
    docs_by_content = list(mongo_db.scraped_questions.find(query_content))
    print(f"Variants found by content pattern: {len(docs_by_content)}")
    
    all_ids = set()
    for doc in docs_by_hash:
        all_ids.add(str(doc['_id']))
    for doc in docs_by_content:
        all_ids.add(str(doc['_id']))
        
    print(f"Total unique variant IDs: {len(all_ids)}")
    for qid in sorted(list(all_ids))[:10]:
        print(f" - {qid}")
    if len(all_ids) > 10:
        print("   ...")

if __name__ == "__main__":
    find_variants_69353700()
