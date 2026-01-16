import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

def find_repaired_question():
    load_dotenv()
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME', 'ai_tutor')]
    
    # The ID we use in the URL is 6932279238273bbfe0cd2d4c
    target_id = "6932279238273bbfe0cd2d4c"
    
    # Try finding in 'questions' collection first
    q = db.questions.find_one({"_id": target_id})
    if not q:
        print("Not found in 'questions' as string ID.")
        from bson.objectid import ObjectId
        try:
            q = db.questions.find_one({"_id": ObjectId(target_id)})
        except:
            q = None
            
    if not q:
        print("Scanning questions for 10 bananas content...")
        q = db.questions.find_one({"question.content": {"$regex": "10 bananas"}})
        if q:
            print(f"Found question by content! ID: {q['_id']}")

    if q:
        print("\n--- QUESTION DATA ---")
        widgets = q.get("question", {}).get("widgets", {})
        orderer = widgets.get("orderer 1", {})
        options = orderer.get("options", {})
        
        print(f"Infinite: {options.get('infinite')}")
        print(f"Correct Options Count: {len(options.get('correctOptions', []))}")
        
        for i, opt in enumerate(options.get('correctOptions', [])):
            print(f"Correct {i}: {opt.get('content')}")
            
        print("\n--- OPTIONS ---")
        for i, opt in enumerate(options.get('options', [])):
            print(f"Option {i}: {opt.get('content')}")
            
        print("\n--- FULL WIDGET JSON ---")
        print(json.dumps(orderer, indent=2))
        
    else:
        print("COULD NOT FIND QUESTION.")

if __name__ == "__main__":
    find_repaired_question()
