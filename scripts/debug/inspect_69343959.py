
import os
import sys
import json
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_69343959():
    qid = "69343959e9b1bbd2029fbbf2"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        # Try as string
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(content)
    print("--- CONTENT END ---")
    
    # Find variants (search by content similarity)
    # Usually questions with same content snippet are variants
    import re
    snippet = content[:50]
    escaped_snippet = re.escape(snippet)
    print(f"\nSearching for variants with snippet: {snippet}")
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
    print(f"Found {len(variants)} variants.")
    for v in variants:
        print(f"ID: {v['_id']}")

if __name__ == "__main__":
    inspect_69343959()
