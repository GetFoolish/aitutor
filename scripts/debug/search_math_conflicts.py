
import os
import sys
import json
from bson import ObjectId

# Add project root to path
original_cwd = os.getcwd()
project_root = original_cwd
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services', 'athenaAPI'))

try:
    from managers.mongodb_manager import mongo_db
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

# Search for questions containing '||' or '|' that might cause table conflicts
print("Searching for questions with potential table/math conflicts...")

query = {
    "question.content": {"$regex": "\\|\\|"}
}

results = list(mongo_db.scraped_questions.find(query).limit(10))

if not results:
    print("No questions found with '||' in content.")
else:
    print(f"Found {len(results)} potential problem questions:")
    for doc in results:
        qid = doc.get('questionId') or str(doc.get('_id'))
        print(f"- ID: {qid}")
        content = doc.get('question', {}).get('content', '')
        print(f"  Content Preview: {content[:100]}...")
