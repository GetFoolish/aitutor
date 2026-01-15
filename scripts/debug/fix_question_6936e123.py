
import os
import sys
import re
from bson.objectid import ObjectId

# Add the project root to sys.path to allow importing from managers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from managers.mongodb_manager import mongo_db

def fix_question_6936e123():
    questions_col = mongo_db.scraped_questions
    
    question_id = "6936e1237b73663f0e7752ff"
    
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
    
    # Update content: replace graphie image with fixed image
    content = doc['question'].get('content', '')
    if not content:
        print("ERROR: doc['question']['content'] is empty!")
        return
        
    # Replace the graphie markdown image link
    # Pattern matches ![some alt text](web+graphie://...)
    pattern = r'!\[.*?\]\(web\+graphie:\/\/.*?\)'
    new_image = "![Graph](/fixed_graphs/graph_6936e123.png)"
    
    new_content = re.sub(pattern, new_image, content)
    
    if new_content == content:
        print("WARNING: Pattern not found in content, trying literal replacement of the known URL...")
        url_to_find = "web+graphie://cdn.kastatic.org/ka-perseus-graphie/d727304e49faf3a98e42adfcc29b7f3b73df6c32"
        if url_to_find in content:
            # Reconstruct the replacement to preserve alt text if possible, 
            # but for simplicity we'll just replace the whole tag if re.sub failed
            pass
    
    result = questions_col.update_one(
        {"_id": doc['_id']},
        {"$set": {"question.content": new_content}}
    )
    
    if result.modified_count > 0:
        print(f"Successfully updated content for question {question_id}")
    else:
        print(f"No changes made (content might already be identical)")

if __name__ == "__main__":
    fix_question_6936e123()
