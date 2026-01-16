
import os
import sys
import json
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def find_asterisks_all():
    query = {
        "question.widgets.image 1.options.backgroundImage.url": {"$regex": "e66dad0513ef84779a581b301c3403a3dea810c3"}
    }
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Checking {len(results)} questions...")
    
    for doc in results:
        qid = doc['_id']
        widgets = doc['question'].get('widgets', {})
        if 'image 1' in widgets:
            opts = widgets['image 1']['options']
            title = opts.get('title', '')
            caption = opts.get('caption', '')
            if "**" in title or "**" in caption:
                print(f"Found ** in {qid}: Title='{title}', Caption='{caption}'")
            else:
                # Print them anyway to see if they just have single *
                print(f"Question {qid}: Title='{title}', Caption='{caption}'")

if __name__ == "__main__":
    find_asterisks_all()
