
import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId
import pprint

# Connection string (from previous context)
MONGO_URI = "mongodb+srv://sherlocked:sherlocked123@cluster0.bbw2k.mongodb.net/athena_db?retryWrites=true&w=majority"

def inspect_question(q_id):
    try:
        client = MongoClient(MONGO_URI)
        db = client['athena_db']
        collection = db['questions']
        
        query = {"_id": ObjectId(q_id)}
        question = collection.find_one(query)
        
        if question:
            print(f"--- Question {q_id} ---")
            # Print hints specifically
            if 'hints' in question:
                print("HINTS:")
                for index, hint in enumerate(question['hints']):
                    print(f"Hint {index}:")
                    pprint.pprint(hint)
            else:
                print("No hints found.")
            
            # Print widgets to see if plotter exists
            if 'widgets' in question:
                print("\nWIDGETS:")
                pprint.pprint(question['widgets'])
        else:
            print(f"Question {q_id} not found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_question("693535d4e61eddfd0c7265ad")
