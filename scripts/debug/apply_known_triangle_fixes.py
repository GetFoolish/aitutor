
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def apply_known_triangle_fixes():
    # Mapping of Broken Hash -> New Local URL
    fixes = {
        # GHI (Angle 65, Side 3)
        "398b806e971ebf7c10dce6fbbf789fe4dfa9a0a9": "/fixed_graphs/question_69360b81_triangle.png",
        # ABC (Angle 55, Side 5)
        "4d5a7152eb4a9381f6727326fe960fe5c818498b": "/fixed_graphs/triangle_fix_693396fb.png"
    }
    
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
                
                for broken_hash, fixed_path in fixes.items():
                    if broken_hash in curr_url and curr_url != fixed_path:
                        bg_img['url'] = fixed_path
                        updated = True
                        break
        
        if updated:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.widgets": widgets}}
            )
            print(f"Updated: {qid}")
            count += 1
            
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    apply_known_triangle_fixes()
