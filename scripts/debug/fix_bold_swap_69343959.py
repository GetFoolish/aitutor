
import os
import sys
import re
from bson.objectid import ObjectId

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

ids = [
    "6930986a9c6f314c42d4240d",
    "69326b402a4ca36772842cfc",
    "69335a9846bd2cf873ae9d2a",
    "6933c87783a8bc4c63d26152",
    "6933e64a1115762db1fdea47",
    "69343959e9b1bbd2029fbbf2",
    "69354b7dcdb2c76c65a52ab3",
    "69367015700579bf9cb92d9e",
    "6936e3927b73663f0e775347",
    "693726a9f24b2a7955fb090a"
]

def swap_bold(content):
    # Step 1: Remove bold from the first paragraph (intro)
    # The intro is the first block starting with ** and ending with ** before the passage.
    # We use a non-greedy match that can span lines and handle internal single *
    content = re.sub(r'(\[\[☃ image 1\]\]\s*)\*\*(.*?)\*\*', r'\1\2', content, flags=re.DOTALL, count=1)
    
    # Step 2: Remove bold from the question line at the end
    # It starts with **Based on the text and ends with ?**
    content = re.sub(r'\*\*(Based on the text, [^*]+\?)\*\*', r'\1', content)
    
    # Step 3: Wrap the passage in bold
    # The passage is between the intro and the question line.
    # Looking at the pattern:
    # Intro end (after register to vote.)
    # Quest start (Based on the text...)
    parts = content.split('\n\n')
    new_parts = []
    
    in_passage = False
    for p in parts:
        trimmed = p.strip()
        if not trimmed:
            new_parts.append(p)
            continue
            
        if "Based on the text" in trimmed:
            in_passage = False
            new_parts.append(p)
            continue
            
        if "register to vote." in trimmed:
            in_passage = True
            new_parts.append(p)
            continue
            
        if in_passage and trimmed:
            # Wrap paragraph in bold if not already
            if not trimmed.startswith('**'):
                new_parts.append(f"**{trimmed}**")
            else:
                new_parts.append(p)
        else:
            new_parts.append(p)
            
    return '\n\n'.join(new_parts)

def apply_fix():
    count = 0
    for qid in ids:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
        if not doc:
            doc = mongo_db.scraped_questions.find_one({"_id": qid})
            
        if doc:
            content = doc['question']['content']
            new_content = swap_bold(content)
            
            if new_content != content:
                mongo_db.scraped_questions.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"question.content": new_content}}
                )
                print(f"Updated: {doc['_id']}")
                count += 1
            else:
                print(f"No change needed for: {doc['_id']}")
                
    print(f"Total updated: {count}")

if __name__ == "__main__":
    apply_fix()
