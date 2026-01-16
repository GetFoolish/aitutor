
import os
import sys
from bson.objectid import ObjectId

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

ids = [
    "6930986a9c6f314c42d4240d",
    "69326b402a4ca36772842cfc",
    "69335a9846bd2cf873ae9d2a",
    "6933c87783a8bc4c63d26152",
    "6933e64a1115762db1fdea47",
    "69343959e9b1bbd2029fbbf2",
    "69354b7dcdb2c76c65a52ab3",
    "69367015700579bf9cb92d9e",
    "6936e3927b73663f0e775347",
    "693726a9f24b2a7955fb090a"
]

for qid in ids:
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
    
    if doc:
        content = doc['question']['content']
        # Print a summary of formatting
        has_intro_bold = "**This excerpt" in content
        has_question_bold = "about?**" in content
        # Check if passage has bold tags
        has_passage_bold = "**Aunt Belle" in content or "**My body" in content
        print(f"ID: {qid} | IntroBold: {has_intro_bold} | QuesBold: {has_question_bold} | PassBold: {has_passage_bold}")
    else:
        print(f"ID: {qid} | NOT FOUND")
