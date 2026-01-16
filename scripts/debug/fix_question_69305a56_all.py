
import os
import sys
import re
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def fix_all_69305a56_variants():
    # The unique URL of the main graph
    TARGET_URL = "web+graphie://cdn.kastatic.org/ka-perseus-graphie/e3e5a87d7bdf70d26e9c8cefbc34bd4ab55e8fac"
    
    # New local paths
    NEW_MAIN = "/fixed_graphs/question_69305a56_main.png"
    NEW_CHOICES = [
        "/fixed_graphs/question_69305a56_choice_0.png",
        "/fixed_graphs/question_69305a56_choice_1.png",
        "/fixed_graphs/question_69305a56_choice_2.png",
        "/fixed_graphs/question_69305a56_choice_3.png"
    ]

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
        
        # 1. Fix Main Image
        if 'image 1' in widgets:
            old_url = widgets['image 1']['options']['backgroundImage']['url']
            if old_url != NEW_MAIN:
                widgets['image 1']['options']['backgroundImage']['url'] = NEW_MAIN
                print(f"  Updated image 1 URL")
                updated = True
            
        # 2. Fix Radio Choices
        if 'radio 1' in widgets:
            choices = widgets['radio 1']['options']['choices']
            if len(choices) != 4:
                print(f"  WARNING: radio 1 has {len(choices)} choices, expected 4. Skipping radio choices update.")
            else:
                for i, choice in enumerate(choices):
                    content = choice['content']
                    new_url = NEW_CHOICES[i]
                    
                    # Regex to match the url part of markdown image: ](web+graphie://...)
                    # This only replaces web+graphie URLs. If it was already fixed (to /fixed_graphs/...), it won't match.
                    content_new = re.sub(r'\]\(web\+graphie:\/\/.*?\)', f']({new_url})', content)
                    
                    if content_new != content:
                        choice['content'] = content_new
                        updated = True
                        print(f"  Updated Choice {i} URL")
        
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
    fix_all_69305a56_variants()
