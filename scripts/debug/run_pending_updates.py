import os
import sys
from pymongo import MongoClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def run_pending_fixes():
    # 1. fix_question_6933fab0_spacing.py
    print("--- Running fix_question_6933fab0_spacing.py ---")
    collection = mongo_db.scraped_questions
    # IDs for 6933fab0 (and variants)
    target_pattern = "$ [["
    replacement = "$[["
    
    query = {"question.content": {"$regex": "\\$ \\[\\[", "$options": "i"}}
    docs = list(collection.find(query))
    print(f"Found {len(docs)} documents with spacing issue.")
    
    for doc in docs:
        content = doc.get('question', {}).get('content', '')
        if target_pattern in content:
            new_content = content.replace(target_pattern, replacement)
            collection.update_one({"_id": doc["_id"]}, {"$set": {"question.content": new_content}})
            print(f"Updated {doc['_id']}")

    # 2. cleanup_69352df3.py (if exists, or similar cleanup)
    # The previous summary mentions cleanup_69352df3.py might not have fully executed.
    # Let's check for remaining \begin{align} or \begin{array} in 69352df3
    print("\n--- Checking 69352df3 cleanup ---")
    qid_69352df3 = "69352df34c2368e642b76932"
    from bson import ObjectId
    try:
        qid = ObjectId(qid_69352df3)
    except:
        qid = qid_69352df3
        
    doc = collection.find_one({"_id": qid})
    if doc:
        content = doc.get('question', {}).get('content', '')
        if "\\begin{align}" in content or "\\begin{array}" in content:
            print(f"Question {qid_69352df3} still has LaTeX artifacts.")
            # We would run the cleanup here if we had the exact script logic
        else:
            print(f"Question {qid_69352df3} looks clean.")

if __name__ == "__main__":
    run_pending_fixes()
