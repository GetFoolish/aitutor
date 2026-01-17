
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_69353e71_graph():
    # The new local image path
    NEW_GRAPH_PATH = "/fixed_graphs/question_69353e71_vector.png"
    
    # Fetch the original question to get the exact content snippet
    origin_qid = "69353e71e61eddfd0c7266aa"
    origin_doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(origin_qid)})
    if not origin_doc:
        print("Original question not found!")
        return
        
    content = origin_doc.get('question', {}).get('content', '')
    # Use the first 50 chars as the snippet, just like the inspect script
    snippet = content[:50] if len(content) > 50 else content
    print(f"Using snippet for search: {repr(snippet)}")
    
    escaped_snippet = re.escape(snippet)
    
    query = {"question.content": {"$regex": escaped_snippet}}
    
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} variants to fix.")
    
    count = 0
    updated_count = 0
    
    for doc in results:
        count += 1
        qid = doc['_id']
        widgets = doc.get('question', {}).get('widgets', {})
        
        updated = False
        
        if 'image 1' in widgets:
            img_options = widgets['image 1'].get('options', {})
            # Handle case where bg image might be missing
            if 'backgroundImage' not in img_options:
                 img_options['backgroundImage'] = {}
                 
            current_url = img_options['backgroundImage'].get('url', '')
            
            if NEW_GRAPH_PATH not in current_url:
                print(f"[{count}] Updating image URL for {qid}")
                print(f"  Old: {current_url}")
                
                img_options['backgroundImage']['url'] = NEW_GRAPH_PATH
                updated = True
                
        if updated:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.widgets": widgets}}
            )
            print(f"  Saved {qid}")
            updated_count += 1
        else:
            print(f"[{count}] No changes needed for {qid}")

    print(f"\nTotal questions processed: {count}")
    print(f"Total questions updated: {updated_count}")

if __name__ == "__main__":
    fix_69353e71_graph()
