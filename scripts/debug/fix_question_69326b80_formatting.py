import json
from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_question_69326b80():
    question_id = "69326b802a4ca36772842d03"
    print(f"Fixing formatting for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": question_id})
    if not question:
        try:
            question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
            
    if not question:
        print("Question not found.")
        return

    # Use a cleaner bolding for the first line to avoid parser confusion
    # Old: ***Bless Me, Ultima* was published in 1972 by Rudolfo Anaya.**
    # New: **_Bless Me, Ultima_ was published in 1972 by Rudolfo Anaya.**
    
    original_content = question.get('question', {}).get('content', '')
    
    # We replace the problematic line. 
    # The leading whitespace/newlines might vary, so we'll be careful.
    
    target_line = "***Bless Me, Ultima* was published in 1972 by Rudolfo Anaya.**"
    replacement_line = "**_Bless Me, Ultima_ was published in 1972 by Rudolfo Anaya.**"
    
    if target_line not in original_content:
        print("Could not find the target title line. Searching for variations...")
        # Try without the leading asterisks or different combinations
        if "**Bless Me, Ultima* was published in 1972 by Rudolfo Anaya.**" in original_content:
             target_line = "**Bless Me, Ultima* was published in 1972 by Rudolfo Anaya.**"
             print("Found variation with 2 asterisks at start.")
    
    new_content = original_content.replace(target_line, replacement_line)
    
    if new_content != original_content:
        print("Applying content update...")
        # Update both question.content and itemData
        mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {"question.content": new_content}}
        )
        
        # Also update itemData if it exists (it's a stringified JSON)
        item_data_str = question.get('itemData')
        if item_data_str:
            item_data = json.loads(item_data_str)
            if 'question' in item_data and 'content' in item_data['question']:
                item_data['question']['content'] = item_data['question']['content'].replace(target_line, replacement_line)
                mongo_db.scraped_questions.update_one(
                    {"_id": question["_id"]},
                    {"$set": {"itemData": json.dumps(item_data)}}
                )
        
        print("Successfully updated question formatting.")
    else:
        print("No changes needed or target line not found.")

if __name__ == "__main__":
    fix_question_69326b80()
