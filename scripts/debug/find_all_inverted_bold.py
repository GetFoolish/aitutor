
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_all_inverted_bold():
    """
    Find all questions where:
    - The intro starts with **In this excerpt or **This excerpt
    - This indicates the intro is bold when it should be normal
    """
    
    # Search for questions with bold intro
    query = {
        "question.content": {
            "$regex": r"\*\*(In this excerpt|This excerpt)",
            "$options": "i"
        }
    }
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions with potentially inverted bold formatting:\n")
    
    # Group by content pattern to find families
    families = {}
    for doc in results:
        qid = str(doc['_id'])
        content = doc.get('question', {}).get('content', '')
        
        # Use first 100 chars as family identifier
        family_key = content[:100]
        
        if family_key not in families:
            families[family_key] = []
        families[family_key].append(qid)
    
    print(f"Found {len(families)} question families:\n")
    
    for i, (key, ids) in enumerate(families.items(), 1):
        print(f"Family {i}: {len(ids)} variants")
        print(f"  First 80 chars: {key[:80]}...")
        print(f"  IDs: {', '.join(ids[:3])}{'...' if len(ids) > 3 else ''}")
        print()
    
    return families

if __name__ == "__main__":
    find_all_inverted_bold()
