
import os
import sys
import time
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def fix_all_6933fab0_spacing():
    # Helper to clean the spacing
    # Target: "$ [[☃ numeric-input 1]]" -> "$[[☃ numeric-input 1]]"
    
    # We search for questions containing the text about juice boxes AND the spaced dollar input
    query = {
        "$and": [
            {"question.content": {"$regex": "juice boxes contains"}},
            {"question.content": {"$regex": "\\$ \\[\\["}} 
        ]
    }
    
    print("Searching for questions with 'juice boxes' and spaced dollar sign...")
    try:
        results = list(mongo_db.scraped_questions.find(query))
        print(f"Found {len(results)} questions to fix.")
    except Exception as e:
        print(f"DB Search failed: {e}")
        return

    count = 0
    for doc in results:
        qid = doc['_id']
        content = doc['question']['content']
        
        print(f"Processing question {qid}...")
        
        # Replace "$ [[" with "$[["
        # We use strict replacement to avoid accidental LaTeX changes
        new_content = content.replace("$ [[", "$[[")
        
        if new_content != content:
            try:
                mongo_db.scraped_questions.update_one(
                    {"_id": qid},
                    {"$set": {"question.content": new_content}}
                )
                print(f"  Fixed spacing for {qid}")
                count += 1
            except Exception as e:
                 print(f"  Update failed for {qid}: {e}")
        else:
            print(f"  No changes needed for {qid}")

    print(f"Finished. Total updated: {count}")

if __name__ == "__main__":
    fix_all_6933fab0_spacing()
