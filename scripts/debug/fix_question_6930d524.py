
import os
import sys
from bson.objectid import ObjectId

# Add the project root to sys.path to allow importing from managers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from managers.mongodb_manager import mongo_db

def fix_question_6930d524():
    questions_col = mongo_db.scraped_questions
    
    question_id = "6930d5240f4b024e7c5dae8b"
    
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
    print(f"Document keys: {doc.keys()}")
    
    # Update content: replace widget with markdown image
    content = doc['question'].get('content', '')
    if not content:
        print("ERROR: doc['question']['content'] is empty!")
        return
        
    new_content = content.replace("![Graph](fixed_graphs/graph_6930d524.png)", "![Graph](/fixed_graphs/graph_6930d524.png)")
    # Also handle the original wedge if it was somehow still there (though we know it's not)
    new_content = new_content.replace("[[☃ image 1]]", "![Graph](/fixed_graphs/graph_6930d524.png)")
    
    result = questions_col.update_one(
        {"_id": doc['_id']},
        {"$set": {"question.content": new_content}}
    )
    
    if result.modified_count > 0:
        print(f"Successfully updated content for question {question_id}")
    else:
        print(f"No changes made (content might already be identical)")

if __name__ == "__main__":
    fix_question_6930d524()
