
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_graph_69353700():
    old_hash = "c6f6211941d057c2f845d5230fbbcfc12f69be70"
    new_url = "/fixed_graphs/question_69353700_graph.png"
    
    # Identify all variants by checking if the hash exists in any widget's backgroundImage URL
    query = {"$or": [
        {"question.widgets.image 1.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 2.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 3.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 4.options.backgroundImage.url": {"$regex": old_hash}},
        {"question.widgets.image 5.options.backgroundImage.url": {"$regex": old_hash}}
    ]}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} documents to fix.")
    
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
    fix_graph_69353700()
