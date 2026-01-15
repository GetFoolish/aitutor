
import os
import sys
from bson.objectid import ObjectId

# Add the project root to sys.path to allow importing from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from managers.mongodb_manager import mongo_db

def fix_question_6933fab0():
    questions_col = mongo_db.scraped_questions
    
    question_id = "6933fab0894ac307482a5c70"
    
    # Try finding as string first
    doc = questions_col.find_one({"_id": question_id})
    if not doc:
        print(f"Not found as string ID, trying as ObjectId...")
        try:
            doc = questions_col.find_one({"_id": ObjectId(question_id)})
            actual_id = ObjectId(question_id)
        except:
            actual_id = question_id
    else:
        actual_id = question_id

    if not doc:
        print(f"ERROR: Question {question_id} not found in scraped_questions!")
        return

    print(f"Found question with ID: {type(doc['_id'])} {doc['_id']}")
    
    # Update main content
    new_content = (
        "A $10$ pack of juice boxes contains $24$ individual juice bottles.\n\n"
        "**What is the cost per bottle?**\n"
        "*Round your answer to the nearest whole cent.*\n\n"
        "$ [[☃ numeric-input 1]]"
    )
    
    result = questions_col.update_one(
        {"_id": doc['_id']},
        {"$set": {"content": new_content}}
    )
    
    if result.modified_count > 0:
        print(f"Successfully updated content for question {question_id}")
    else:
        print(f"No changes made (content might already be identical)")

if __name__ == "__main__":
    fix_question_6933fab0()
