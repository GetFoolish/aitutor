
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def dump_full_content():
    qid = "6937182936a35a5a350979a4"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    
    if not doc:
        print("Question not found.")
        return
        
    content = doc.get('question', {}).get('content', '')
    
    print("=== FULL CONTENT ===")
    print(content)
    print("\n\n=== PARAGRAPHS (split by \\n\\n) ===")
    parts = content.split('\n\n')
    for i, p in enumerate(parts):
        print(f"\n--- Paragraph {i} ---")
        print(repr(p[:150]))

if __name__ == "__main__":
    dump_full_content()
