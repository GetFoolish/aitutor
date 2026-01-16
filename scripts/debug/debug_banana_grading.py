import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

def debug_grading():
    load_dotenv()
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME', 'ai_tutor')]
    
    question_id = "6932279238273bbfe0cd2d4c"
    q = db.questions.find_one({"_id": question_id})
    if not q:
        from bson.objectid import ObjectId
        try:
            q = db.questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
    
    if not q:
        # Try finding by slug or content
        q = db.questions.find_one({"question.content": {"$regex": "10 bananas"}})

    widgets = q.get("question", {}).get("widgets", {})
    orderer = widgets.get("orderer 1", {})
    options = orderer.get("options", {})
    correct_options = options.get("correctOptions", [])
    
    print(f"Found {len(correct_options)} correct options")
    
    for i, opt in enumerate(correct_options):
        content = opt.get("content", "")
        print(f"Item {i}: {content}")
        if "ATHENA_HTML_SAFE" in content or "ATHENAHTMLSAFE" in content:
            print(f"!!! CRITICAL: Item {i} has corruption !!!")

    # Simulate what OrdererWidget returns
    repaired_banana = "![A banana.](https://cdn.kastatic.org/ka-perseus-graphie/9bb69f238fb7a981c06fb2ce69ca3f9e131add62.png)"
    print(f"\nComparing against target: {repaired_banana}")
    
    matches = 0
    for opt in correct_options:
        if opt.get("content") == repaired_banana:
            matches += 1
    
    print(f"Total matches: {matches}")
    
    if matches == len(correct_options) and len(correct_options) == 10:
        print("Grading logic SHOULD pass if userAnswer is an array of 10 bananas.")
    else:
        print("Grading logic WILL FAIL.")

if __name__ == "__main__":
    debug_grading()
