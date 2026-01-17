
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_6937182936():
    qid = "6937182936a35a5a350979a4"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START (first 500 chars) ---")
    print(content[:500])
    print("--- CONTENT END ---")
    
    # Check for bold formatting
    has_intro_bold = "**In this excerpt" in content or "**This excerpt" in content
    has_passage_bold = "**The map my clients" in content or "**But I kept" in content
    print(f"\nIntro has bold: {has_intro_bold}")
    print(f"Passage has bold: {has_passage_bold}")

    # Find variants
    snippet = content[:50]
    escaped_snippet = re.escape(snippet)
    print(f"\nSearching for variants with snippet: {snippet}")
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
    print(f"Found {len(variants)} variants.")
    for v in variants:
        v_qid = v['_id']
        print(f"ID: {v_qid}")

if __name__ == "__main__":
    inspect_6937182936()
