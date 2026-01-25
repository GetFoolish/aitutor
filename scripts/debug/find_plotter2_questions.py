
import os
from pymongo import MongoClient
import json
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME', 'ai_tutor')

def find_questions():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Collections to check
        collections = ['scraped_questions', 'perseus_questions', 'dash_questions']
        
        search_term = "plotter 2"
        found_ids = set()
        
        for coll_name in collections:
            print(f"Searching in {coll_name}...")
            collection = db[coll_name]
            
            # Search in content and hints
            query = {
                "$or": [
                    {"question.content": {"$regex": search_term, "$options": "i"}},
                    {"hints.content": {"$regex": search_term, "$options": "i"}},
                    {"question.hints.content": {"$regex": search_term, "$options": "i"}}
                ]
            }
            
            results = collection.find(query, {"_id": 1, "title": 1})
            for doc in results:
                q_id = str(doc['_id'])
                found_ids.add(q_id)
                print(f"Found Question ID: {q_id} | Title: {doc.get('title', 'N/A')}")
        
        print(f"\nTotal unique IDs found: {len(found_ids)}")
        print(f"IDs: {list(found_ids)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_questions()
