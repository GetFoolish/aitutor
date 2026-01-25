
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import json

# Connection string
MONGO_URI = "mongodb+srv://sherlocked:sherlocked123@cluster0.bbw2k.mongodb.net/athena_db?retryWrites=true&w=majority"

def inspect_question(q_id):
    try:
        client = MongoClient(MONGO_URI)
        db = client['athena_db']
        collection = db['questions']
        
        query = {"_id": ObjectId(q_id)}
        question = collection.find_one(query)
        
        if not question:
            print(f"Question {q_id} not found.")
            return

        print("=== CONTENT ===")
        print(question.get('content'))
        
        print("\n=== WIDGETS ===")
        widgets = question.get('widgets', {})
        for w_id, w_data in widgets.items():
            print(f"Widget: {w_id} ({w_data.get('type')})")
            print(json.dumps(w_data.get('options', {}), indent=2))
            
        print("\n=== HINTS ===")
        for i, hint in enumerate(question.get('hints', [])):
            print(f"Hint {i+1}:")
            print(hint.get('content'))
            print("Widgets:", hint.get('widgets', {}).keys())

            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_question("693535d4e61eddfd0c7265ad")
