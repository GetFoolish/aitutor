
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import json

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
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_question("6931b1aff0cd8d47c9679eb8")
