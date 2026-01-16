import os
import sys
from pymongo import MongoClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_trig_questions():
    collection = mongo_db.scraped_questions
    
    # Search for questions with trigonometry tables in content
    # Look for "Angle |" and common degree symbols or "ratio"
    query = {
        "question.content": {"$regex": "Angle \\|.*\\|.*\\|", "$options": "i"}
    }
    
    results = list(collection.find(query))
    print(f"Found {len(results)} potential trig table questions.")
    
    for doc in results:
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        print(f"\nID: {qid}")
        # Print the table part
        if "Angle |" in content:
            start = content.find("Angle |")
            end = content.find("\n\n", start)
            if end == -1: end = start + 500
            print(content[start:end])

if __name__ == "__main__":
    find_trig_questions()
