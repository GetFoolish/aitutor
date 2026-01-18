import os
import sys
from bson import ObjectId

# Add project root to path for shared imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_question():
    qid = "6935ba4d04cecc14353196f3"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    
    if not doc:
        print(f"Question {qid} not found.")
        return

    print(f"ID: {doc['_id']}")
    content = doc.get('question', {}).get('content', '')
    print(f"Content:\n---\n{content}\n---")
    
    # Try to find variants with similar content
    snippet = "These are the component forms of vectors"
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": snippet}}))
    print(f"Found {len(variants)} variants.")
    for v in variants:
        print(f"- {v['_id']}")

if __name__ == "__main__":
    inspect_question()
