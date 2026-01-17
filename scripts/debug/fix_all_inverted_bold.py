
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
    Swap bold and normal text for reading comprehension questions.
    Pattern:
    - Remove bold from intro (**In this excerpt... or **This excerpt...)
    - Remove bold from question line at the end
    - Add bold to the passage paragraphs in between
    """
    
    # Step 1: Remove bold from the first intro paragraph after image
    # Match the first **...** block after [[☃ image 1]]
    content = re.sub(
        r'(\[\[☃ image 1\]\]\s*)\*\*(.*?)\*\*',
        r'\1\2',
        content,
        flags=re.DOTALL,
        count=1
    )
    
    # Step 2: Remove bold from question lines (various patterns)
    # Pattern: **Which/What/How/Based on... ?**
    content = re.sub(
        r'\*\*((?:Which|What|How|Based on|According to)[^*]+?\?)\*\*',
        r'\1',
        content,
        flags=re.IGNORECASE
    )
    
    # Step 3: Add bold to passage paragraphs
    # Split by double newlines to find paragraphs
    parts = content.split('\n\n')
    new_parts = []
    
    in_passage = False
    for p in parts:
        trimmed = p.strip()
        if not trimmed:
            new_parts.append(p)
            continue
        
        # Skip if it's a widget reference
        if '[[☃' in trimmed:
            new_parts.append(p)
            continue
            
        # Check if we're entering the passage (after intro ends)
        # Intro typically ends with patterns like "map.**" or "novel.**"
        if re.search(r'\.\*\*\s*$', trimmed):
            in_passage = True
            new_parts.append(p)
            continue
        
        # Check if we're at a question (exit passage)
        if re.match(r'^(Which|What|How|Based on|According to)', trimmed, re.IGNORECASE):
            in_passage = False
            new_parts.append(p)
            continue
            
        # If in passage and not already bold, make it bold
        if in_passage and trimmed and not trimmed.startswith('**'):
            # Check if it's a numbered paragraph
            if re.match(r'^\d+\.', trimmed):
                new_parts.append(f"**{trimmed}**")
            elif len(trimmed) > 20:  # Only bold substantial paragraphs
                new_parts.append(f"**{trimmed}**")
            else:
                new_parts.append(p)
        else:
            new_parts.append(p)
            
    return '\n\n'.join(new_parts)

def fix_all_inverted_bold():
    # Find all questions with bold intro
    query = {
        "question.content": {
            "$regex": r"\*\*(In this excerpt|This excerpt)",
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
