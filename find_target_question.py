
import os
from dotenv import load_dotenv
load_dotenv()
from managers.mongodb_manager import mongo_db
import json

def find_question():
    print("Searching for question with 'g(b)=5b-9'...")
    # Use a direct string search instead of regex for speed if possible, 
    # but MongoDB regex is usually okay if indexed. 
    # Here we'll just try to find ANY question with this string.
    query = {"question.content": {"$regex": "g\\(b\\)=5b-9"}}
    doc = mongo_db.scraped_questions.find_one(query)
    
    if doc:
        print(f"Found Question ID: {doc['_id']}")
        print("Raw Question Content:")
        print(doc['question']['content'])
        print("\n--- JSON Snapshot ---")
        # Print a bit more of the doc
        print(json.dumps({
            "_id": str(doc["_id"]),
            "slug": doc.get("slug"),
            "question": {
                "content": doc["question"]["content"]
            }
        }, indent=2))
    else:
        print("Question not found.")

if __name__ == "__main__":
    find_question()
