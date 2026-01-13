from managers.mongodb_manager import mongo_db
from bson import ObjectId
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
                
        print("CONTENT:")
        print(question.get('question', {}).get('content', ''))
        print("\nWIDGETS:")
        widgets = question.get('question', {}).get('widgets', {})
        for name, data in widgets.items():
            print(f"--- {name} ({data.get('type')}) ---")
            print(json.dumps(data.get('options', {}), indent=2))
        
        print("\nHINTS:")
        hints = question.get('hints', [])
        for i, hint in enumerate(hints):
            print(f"--- Hint {i} ---")
            print(hint.get('content', ''))
    else:
        print("Question not found.")

if __name__ == "__main__":
    inspect_question("69345a15bcfb8e91f4cdda1c")
