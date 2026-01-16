
import os
import sys
import json
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def inspect_question():
    qid = "69324cd92e5f91c2481807bc"
    print(f"Inspecting question {qid}...")
    
    try:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        if not doc:
            doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
            
        if not doc:
            print("Question not found!")
            return
            
        print("FOUND QUESTION:")
        # Print main image widget and radio widget
        widgets = doc.get('question', {}).get('widgets', {})
        
        print("\n--- CONTENT ---")
        print(doc.get('question', {}).get('content', ''))
        
        if 'image 1' in widgets:
            print("\n--- image 1 ---")
            print(json.dumps(widgets['image 1'], indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_question()
