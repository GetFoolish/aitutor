
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def swap_bold_69360b81(content):
    # Step 1: Unbold the instruction paragraph
    new_content = re.sub(
        r'\*\*Use the table to approximate (.*?) in the triangle below\.\*\*',
        r'Use the table to approximate \1 in the triangle below.',
        content
    )
    
    # Step 2: Bold the first two paragraphs
    parts = new_content.split('\n\n')
    if len(parts) >= 2:
        # Paragraph 1
        if not parts[0].strip().startswith('**') and len(parts[0].strip()) > 10:
             parts[0] = f"**{parts[0].strip()}**"
        
        # Paragraph 2
        if not parts[1].strip().startswith('**') and len(parts[1].strip()) > 10:
             parts[1] = f"**{parts[1].strip()}**"
             
    return '\n\n'.join(parts)

def fix_69360b81_group():
    snippet = "ratios for angle measures"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} documents to fix.")
    
    count = 0
    for doc in docs:
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        
        new_content = swap_bold_69360b81(content)
        
        if new_content != content:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.content": new_content}}
            )
            print(f"Updated: {qid}")
            count += 1
        else:
            print(f"No changes needed or already fixed for: {qid}")
            
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    fix_69360b81_group()
