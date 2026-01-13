from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId
import json

def debug_db(question_id):
    print(f"Debugging DB for question: {question_id}")
    
    # Try direct string find
    q_str = mongo_db.scraped_questions.find_one({"_id": question_id})
    if q_str:
        print(f"Found with string ID. Content: {repr(q_str['question']['content'][:100])}...")
        print(f"Full Content: {repr(q_str['question']['content'])}")
    
    # Try ObjectId find
    try:
        q_obj = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        if q_obj:
            print(f"Found with ObjectId. Content: {repr(q_obj['question']['content'][:100])}...")
            print(f"Full Content: {repr(q_obj['question']['content'])}")
    except:
        print("Invalid ObjectId format")

if __name__ == "__main__":
    debug_db("6932a69125f2e0b37ec6039c")
