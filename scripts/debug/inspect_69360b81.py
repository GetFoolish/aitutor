
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_69360b81():
    qid = "69360b810aabe66864660c1a"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(repr(content))
    print("--- CONTENT END ---")
    
    if content:
        snippet = "ratios for angle measures"
        print(f"\nSearching for variants with snippet: {repr(snippet)}")
        variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": snippet}}))
        print(f"Found {len(variants)} variants.")
        for v in variants:
            print(f"ID: {v['_id']}")

if __name__ == "__main__":
    inspect_69360b81()
