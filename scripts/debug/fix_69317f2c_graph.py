
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_69317f2c_graph():
    # The new local image path
    NEW_GRAPH_PATH = "/fixed_graphs/question_69317f2c_graph.png"
    
    # Get original question content to capture the exact string for regex
    qid_original = "69317f2c47a2cb48fc68c308"
    doc_original = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid_original)})
    if not doc_original:
        print("Original question not found!")
        return

    content = doc_original.get('question', {}).get('content', '')
    snippet = content[:50]
    escaped_snippet = re.escape(snippet)
    print(f"Using snippet for search: {snippet}")

    query = {"question.content": {"$regex": escaped_snippet}}
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} potential variants to fix.")
    
    count = 0
    updated_count = 0
    
    for doc in results:
        count += 1
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        
        updated = False
        
        # Regex to find the image in markdown
        # Pattern: ![alt text](url)
        # We want to replace the url if it's not already fixed
        # But we need to be careful not to replace other images if any (though unlikely here)
        # The image seems to be at the start or early in text.
        
        # Regex capture: ![...](...)
        match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        
        if match:
            alt_text = match.group(1)
            current_url = match.group(2)
            
            if NEW_GRAPH_PATH not in current_url:
                print(f"[{count}] Updating content image for {qid}")
                print(f"  Old URL: {current_url}")
                
                # Replace the whole image tag with new one
                # We can keep the alt text or use a generic one? 
                # User didn't specify alt text, but keeping original is safer.
                new_image_markdown = f"![{alt_text}]({NEW_GRAPH_PATH})"
                
                # Replace in content
                # Use replace (string) to avoid regex escaping issues if url has special chars
                # But we constructed the match from regex, so we know exact string
                full_match_str = match.group(0)
                new_content = content.replace(full_match_str, new_image_markdown)
                
                if new_content != content:
                    widgets = doc.get('question', {}).get('widgets', {}) # Get widgets just to preserve them if needed (update touches content)
                    
                    mongo_db.scraped_questions.update_one(
                        {"_id": qid},
                        {"$set": {"question.content": new_content}}
                    )
                    updated = True
                    print(f"  Saved {qid}")
        
        if not updated:
            # Check if it was already fixed
            if NEW_GRAPH_PATH in content:
                 print(f"[{count}] Already fixed {qid}")
            else:
                 print(f"[{count}] No image found or no changes needed {qid}")

    print(f"\nTotal questions processed: {count}")
    print(f"Total questions updated: {updated_count}")

if __name__ == "__main__":
    fix_69317f2c_graph()
