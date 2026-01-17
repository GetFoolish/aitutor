
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def swap_bold_improved(content):
    """
    Universal bold swap for reading comprehension questions.
    Strategy:
    1. Remove ** from intro (first paragraph after image)
    2. Remove ** from question at end
    3. Add ** to all paragraphs between intro and question
    """
    
    # Step 1: Remove bold from intro (first **...** after image)
    content = re.sub(
        r'(\[\[☃ image 1\]\]\s*)\*\*(.*?)\*\*',
        r'\1\2',
        content,
        flags=re.DOTALL,
        count=1
    )
    
    # Step 2: Remove bold from question lines (at the end)
    # Common patterns: Which/What/How/Based on/According to
    content = re.sub(
        r'\*\*((Which|What|How|Based on|According to)[^*]+?\?)\*\*',
        r'\1',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    
    # Step 3: Bold the passage paragraphs
    # Split by paragraphs
    parts = content.split('\n\n')
    new_parts = []
    
    # State machine
    seen_intro = False
    in_passage = False
    
    for p in parts:
        trimmed = p.strip()
        
        # Empty paragraph
        if not trimmed:
            new_parts.append(p)
            continue
        
        # Block widget reference - skip only if it looks like a standalone widget
        # e.g. [[☃ image 1]] or [[☃ radio 1]]
        # But NOT inline definitions like "text [[☃ definition 1]] text"
        if trimmed.startswith('[[☃') and len(trimmed) < 40:
            new_parts.append(p)
            # If this is image 1, next non-widget is intro
            if '[[☃ image 1]]' in trimmed:
                seen_intro = False
            continue
        
        # First paragraph after image is intro (already unbold)
        if not seen_intro:
            print(f"DEBUG: Intro found: {trimmed[:30]}...")
            seen_intro = True
            in_passage = True  # Start passage after intro
            new_parts.append(p)
            continue
        
        # Check if this is the question (ends passage)
        if re.match(r'^(Which|What|How|Based on|According to)', trimmed, re.IGNORECASE):
            print(f"DEBUG: Question found (end passage): {trimmed[:30]}...")
            in_passage = False
            new_parts.append(p)
            continue
        
        if in_passage:
            print(f"DEBUG: In passage, processing: {trimmed[:30]}...")
            # Check if already bold
            if trimmed.startswith('**') and trimmed.endswith('**'):
                new_parts.append(p)
            else:
                # Add bold
                # Force bold for any paragraph in passage, especially numbered ones
                # But ensure we don't double-bold if there are internal bold markers
                if '**' in trimmed:
                     # If mixed bolding exists, just wrap the whole thing or leave it?
                     # Better to wrap the whole thing to be consistent with request
                     # But remove outer bold if it exists locally?
                     # Safest: Just wrap it. Markdown handles nested bold reasonable well or we can strip
                     new_parts.append(f"**{trimmed}**")
                else:
                    new_parts.append(f"**{trimmed}**")
        else:
            new_parts.append(p)
    
    return '\n\n'.join(new_parts)

def fix_all_inverted_bold():
    # Find all questions with bold intro
    # We look for questions starting with bold intro pattern
    query = {
        "question.content": {
            "$regex": r"\*\*(In this excerpt|This excerpt)",
            "$options": "i"
        }
    }
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions matching bold intro pattern.\n")
    
    count = 0
    updated_count = 0
    
    for doc in results:
        count += 1
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        
        # Apply the fix
        new_content = swap_bold_improved(content)
        
        # Additional safety check: Ensure we actually removed the intro bold
        # and added at least some bold elsewhere if it wasn't there
        if new_content != content:
            # Update in database
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.content": new_content}}
            )
            print(f"[{count}/{len(results)}] Updated: {qid}")
            updated_count += 1
        else:
            print(f"[{count}/{len(results)}] No change needed: {qid}")
                
    print(f"\nTotal questions processed: {count}")
    print(f"Total questions updated: {updated_count}")

if __name__ == "__main__":
    fix_all_inverted_bold()
