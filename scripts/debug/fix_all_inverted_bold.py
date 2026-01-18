
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def swap_bold_universal(content):
    """
    Strictly swap bold and normal text for paragraphs.
    """
    parts = content.split('\n\n')
    new_parts = []
    for p in parts:
        trimmed = p.strip()
        if not trimmed or '[[☃' in trimmed:
            new_parts.append(p)
            continue
            
        # If it's bold, make it normal
        if trimmed.startswith('**') and trimmed.endswith('**'):
            new_parts.append(trimmed[2:-2])
        # If it's normal, make it bold
        else:
            new_parts.append(f"**{trimmed}**")
            
    return '\n\n'.join(new_parts)

def fix_all_inverted_bold():
    # Find all questions with bold intro
    query = {
        "question.content": {
            "$regex": r"\*\*(In this excerpt|This excerpt|This passage is adapted)",
            "$options": "i"
        }
    }
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions to fix.\n")
    
    count = 0
    for doc in results:
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        
        # Apply the fix
        new_content = swap_bold_universal(content)
        
        if new_content != content:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.content": new_content}}
            )
            print(f"Updated: {qid}")
            count += 1
        else:
            print(f"No change: {qid}")
                
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    fix_all_inverted_bold()
