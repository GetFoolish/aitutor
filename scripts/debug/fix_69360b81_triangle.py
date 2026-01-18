
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_triangle_image_69360b81():
    old_hash = "398b806e971ebf7c10dce6fbbf789fe4dfa9a0a9"
    new_url = "/fixed_graphs/question_69360b81_triangle.png"
    
    snippet = "ratios for angle measures"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} documents in the family.")
    
    count = 0
    for doc in docs:
        qid = doc['_id']
        widgets = doc.get('question', {}).get('widgets', {})
        updated = False
        
        for widget_name, widget_data in widgets.items():
            if widget_data.get('type') == 'image':
                img_opt = widget_data.get('options', {})
                bg_img = img_opt.get('backgroundImage', {})
                curr_url = bg_img.get('url', '')
                if old_hash in curr_url:
                    bg_img['url'] = new_url
                    updated = True
        
        if updated:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.widgets": widgets}}
            )
            print(f"Updated image URL for: {qid}")
            count += 1
            
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    fix_triangle_image_69360b81()
