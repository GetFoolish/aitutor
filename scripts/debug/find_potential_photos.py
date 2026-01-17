
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_potential_photos():
    # Search for questions with images that look like photos but might be inverting
    # We look for .jpg extension or "photo" in alt text
    results = mongo_db.scraped_questions.find({
        "$or": [
            {"question.widgets.image 1.options.backgroundImage.url": {"$regex": "\.jpe?g", "$options": "i"}},
            {"question.widgets.image 1.options.alt": {"$regex": "photo|photograph|portrait|landscape|nature|sky|star", "$options": "i"}}
        ]
    }).limit(20)
    
    print("Potential photos found in DB:")
    for r in results:
        qid = r['_id']
        url = r.get('question', {}).get('widgets', {}).get('image 1', {}).get('options', {}).get('backgroundImage', {}).get('url')
        alt = r.get('question', {}).get('widgets', {}).get('image 1', {}).get('options', {}).get('alt')
        print(f"ID: {qid} | URL: {url} | Alt: {alt}")

if __name__ == "__main__":
    find_potential_photos()
