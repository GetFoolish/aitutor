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
        
        # Print only the choices to see what's stored
        widgets = question.get("question", {}).get("widgets", {})
        for widget_key, widget_data in widgets.items():
            if widget_data.get("type") == "radio":
                choices = widget_data.get("options", {}).get("choices", [])
                print(f"\nFound {len(choices)} choices:")
                for i, choice in enumerate(choices):
                    print(f"\nChoice {i}:")
                    print(f"  Content: {choice.get('content', '')[:200]}...")
                    print(f"  Correct: {choice.get('correct', False)}")
    else:
        print("Question not found.")

if __name__ == "__main__":
    inspect_question("6932e9ff488c4a5c22f22f5b")
