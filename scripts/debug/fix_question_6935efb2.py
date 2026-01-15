
import os
import sys
from bson.objectid import ObjectId

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from managers.mongodb_manager import mongo_db

def fix_question_6935efb2():
    qid = "6935efb23038188721d6fd2d"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        print("Question not found")
        return
        
    widgets = doc['question'].get('widgets', {})
    updated = False
    
    # Check image 1 caption
    if 'image 1' in widgets:
        caption = widgets['image 1'].get('options', {}).get('caption', '')
        if "*" in caption:
            new_caption = caption.replace("*", "")
            widgets['image 1']['options']['caption'] = new_caption
            print(f"Updated image 1 caption: '{caption}' -> '{new_caption}'")
            updated = True

    # Check explanation 1 just in case, though user only mentioned image title
    if 'explanation 1' in widgets:
        explanation = widgets['explanation 1'].get('options', {}).get('explanation', '')
        if "*" in explanation:
            new_explanation = explanation.replace("*", "")
            widgets['explanation 1']['options']['explanation'] = new_explanation
            print(f"Updated explanation 1: '{explanation.strip()}' -> '{new_explanation.strip()}'")
            updated = True
            
    if updated:
        result = mongo_db.scraped_questions.update_one(
            {"_id": ObjectId(qid)},
            {"$set": {"question.widgets": widgets}}
        )
        if result.modified_count > 0:
            print("Successfully updated database record.")
        else:
            print("No modification made to database (maybe already fixed).")
    else:
        print("No asterisks found to remove.")

if __name__ == "__main__":
    fix_question_6935efb2()
