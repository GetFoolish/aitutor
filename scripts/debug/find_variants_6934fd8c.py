
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_variants_6934fd8c():
    hashes = [
        "b3db47b21c9e3744dbf2af4aa0f80e751c2ed590",
        "e4bf0c1da327b6e8f958112c6dd5612f60ef0a92",
        "5700064c4fdc1370631c69d2181568a80da6649d"
    ]
    
    all_variant_ids = set()
    
    # 1. Search by hashes in widgets content (Markdown links)
    for h in hashes:
        query = {"question.widgets.radio 1.options.choices.content": {"$regex": h}}
        docs = list(mongo_db.scraped_questions.find(query))
        print(f"Variants found by hash {h[:10]}: {len(docs)}")
        for d in docs:
            all_variant_ids.add(str(d['_id']))
            
    # 2. Search by content pattern: "Baseball team | Runs score"
    snippet = "Baseball team | Runs score"
    query_snippet = {"question.content": {"$regex": snippet}}
    docs_snippet = list(mongo_db.scraped_questions.find(query_snippet))
    print(f"Variants found by content snippet: {len(docs_snippet)}")
    for d in docs_snippet:
        all_variant_ids.add(str(d['_id']))
        
    print(f"Total unique variant IDs: {len(all_variant_ids)}")
    for qid in sorted(list(all_variant_ids))[:10]:
        print(f" - {qid}")
    if len(all_variant_ids) > 10:
        print("   ...")

if __name__ == "__main__":
    find_variants_6934fd8c()
