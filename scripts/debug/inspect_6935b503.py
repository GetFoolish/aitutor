
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_6935b503():
    qid = "6935b50304cecc1435319657"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(repr(content))
    print("--- CONTENT END ---")
    
    # Try to find variants based on a snippet of the passage (which is currently not bolded if inverted)
    # Actually, if it's inverted, the passage might be normal text.
    # Looking at the content from the user request context, let's see.
    
    # Let's print the first part of the content to find variants
    if content:
        snippet = content[:100]
        import re
        escaped_snippet = re.escape(snippet)
        print(f"\nSearching for variants with snippet: {repr(snippet)}")
        variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
        print(f"Found {len(variants)} variants.")
        for v in variants:
            print(f"ID: {v['_id']}")

if __name__ == "__main__":
    inspect_6935b503()
