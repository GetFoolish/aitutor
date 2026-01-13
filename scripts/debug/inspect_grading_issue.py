from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId
import json
from datetime import datetime

def inspect_question(question_id):
    print(f"Inspecting question: {question_id}")
    question = mongo_db.scraped_questions.find_one({"_id": question_id})
    if not question:
        try:
            question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
            
    if question:
        class MongoEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, ObjectId):
                    return str(obj)
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
                
        print(json.dumps(question, indent=2, cls=MongoEncoder))
    else:
        print("Question not found.")

if __name__ == "__main__":
    inspect_question("69317e1c47a2cb48fc68c2e8")
