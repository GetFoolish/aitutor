
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
    """
    
    # Step 1: Remove bold from the first intro paragraph after image
    content = re.sub(
        r'(\[\[☃ image 1\]\]\s*)\*\*(.*?)\*\*',
        r'\1\2',
        content,
        flags=re.DOTALL,
        count=1
    )
    
    # Step 2: Remove bold from question lines
    content = re.sub(
        r'\*\*((?:Which|What|How|Based on|According to)[^*]+?\?)\*\*',
        r'\1',
        content,
        flags=re.IGNORECASE
    )
    
    # Step 3: Add bold to passage paragraphs
    parts = content.split('\n\n')
    new_parts = []
    
    in_passage = False
    for p in parts:
        trimmed = p.strip()
        if not trimmed:
            new_parts.append(p)
            continue
        
        # Skip widget references
        if '[[☃' in trimmed:
            new_parts.append(p)
            continue
            
        # Detect end of intro (usually ends with .**)
        if re.search(r'\.\*\*\s*$', trimmed):
            in_passage = True
            new_parts.append(p)
            continue
        
        # Detect question start
        if re.match(r'^(Which|What|How|Based on|According to)', trimmed, re.IGNORECASE):
            in_passage = False
            new_parts.append(p)
            continue
            
        # Bold passage paragraphs
        if in_passage and trimmed and not trimmed.startswith('**'):
            if re.match(r'^\d+\.', trimmed) or len(trimmed) > 20:
                new_parts.append(f"**{trimmed}**")
            else:
                new_parts.append(p)
        else:
            new_parts.append(p)
            
    return '\n\n'.join(new_parts)

def test_on_one():
    qid = "6937182936a35a5a350979a4"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    
    if not doc:
        print("Question not found.")
        return
        
    content = doc.get('question', {}).get('content', '')
    
    print("=== BEFORE ===")
    print(content[:800])
    print("\n\n=== AFTER ===")
    new_content = swap_bold_universal(content)
    print(new_content[:800])
    
    print("\n\n=== COMPARISON ===")
    print(f"Changed: {content != new_content}")

if __name__ == "__main__":
    test_on_one()
