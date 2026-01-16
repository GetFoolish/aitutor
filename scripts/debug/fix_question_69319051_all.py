
import os
import sys
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def fix_all_69319051_variants():
    # The unique URL of the main graph
    TARGET_URL = "web+graphie://cdn.kastatic.org/ka-perseus-graphie/bcdaedd0eea074b2fc7d1c383ae3a12b0fbb15fc"
    
    # New local path
    NEW_MAIN = "/fixed_graphs/question_69319051_main.png"

    # Find all questions with this graph in 'image 1'
    query = {
        "question.widgets.image 1.options.backgroundImage.url": TARGET_URL
    }
    
    print(f"Searching for questions with URL: {TARGET_URL}")
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions to fix.")
    
    count = 0
    for doc in results:
        qid = doc['_id']
        print(f"Processing question {qid}...")
        
        widgets = doc['question'].get('widgets', {})
        updated = False
        
        # Fix Internal Image Widget URL
        if 'image 1' in widgets:
            old_url = widgets['image 1']['options']['backgroundImage']['url']
            if old_url != NEW_MAIN:
                widgets['image 1']['options']['backgroundImage']['url'] = NEW_MAIN
                print(f"  Updated image 1 URL")
                updated = True
        
        if updated:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.widgets": widgets}}
            )
            print(f"  Saved changes to DB for {qid}")
            count += 1
        else:
            print(f"  No changes needed for {qid}")
            
    print(f"Finished. Total updated: {count}")

if __name__ == "__main__":
    fix_all_69319051_variants()
