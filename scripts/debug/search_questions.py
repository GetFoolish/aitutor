
import os
import sys
from bson import ObjectId

# Add project root to path
# Script is in scripts/debug/
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

SEARCH_TERM = "[[☃ interactive-graph"
print(f"SEARCHING FOR: {SEARCH_TERM} questions")

# Search in scraped_questions
results = mongo_db.scraped_questions.find({
    "question.content": {"$regex": SEARCH_TERM.replace("[", "\\["), "$options": "i"}
}).limit(5)

for doc in results:
    print(f"ID: {doc['_id']} | Title: {doc.get('title', 'N/A')}")
