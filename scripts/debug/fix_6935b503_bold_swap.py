
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def swap_bold_6935b503(content):
    # Pattern 1: Intro starts with ** and ends with **
    content = re.sub(
        r'\*\*This passage is adapted from Sherwood Anderson[’\']s [“"]Departure,[”"] which was originally published in 1919\.\*\*',
        r'This passage is adapted from Sherwood Anderson’s “Departure,” which was originally published in 1919.',
        content
    )
    
    # Pattern 2: Second intro bit with weird formatting
    content = re.sub(
        r'\*This passage is about George Willard[’\']s departure from his hometown, the fictional Winesburg, Ohio\.\*\*\*',
        r'This passage is about George Willard’s departure from his hometown, the fictional Winesburg, Ohio.',
        content
    )
    
    # Pattern 3: Question stem
    # Allow any question from Which to ? inside **
    content = re.sub(
        r'\*\*((?:Which|What|How|Based on|According to)[^*]+?\?)\*\*',
        r'\1',
        content,
        flags=re.IGNORECASE
    )

    # Step: Bold the paragraphs
    parts = content.split('\n\n')
    new_parts = []
    for p in parts:
        trimmed = p.strip()
        # If it's a numbered paragraph (e.g. "1. George ...") and not bold, make it bold
        if re.match(r'^\s*\d+\.\s+\w', trimmed) and not trimmed.startswith('**'):
            new_parts.append(f"**{trimmed}**")
        else:
            new_parts.append(p)
            
    return '\n\n'.join(new_parts)

def fix_6935b503_group():
    snippet = "Sherwood Anderson"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} documents to fix.")
    
    count = 0
    for doc in docs:
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        
        new_content = swap_bold_6935b503(content)
        
        if new_content != content:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.content": new_content}}
            )
            print(f"Updated: {qid}")
            count += 1
        else:
            print(f"No changes needed or pattern mismatched for: {qid}")
            
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    fix_6935b503_group()
