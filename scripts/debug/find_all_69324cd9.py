import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_all_69324cd9_variants():
    collection = mongo_db.scraped_questions
    # Search by a unique segment of the text
    search_text = "The tropical and subtropical moist broadleaf forests biome has warm temperatures"
    query = {"question.content": {"$regex": search_text, "$options": "i"}}
    docs = list(collection.find(query))
    print(f"Total variants found by content: {len(docs)}")
    
    for doc in docs:
        img_url = doc.get('question', {}).get('widgets', {}).get('image 1', {}).get('options', {}).get('backgroundImage', {}).get('url', 'N/A')
        print(f"ID: {doc['_id']} | URL: {img_url}")

if __name__ == "__main__":
    find_all_69324cd9_variants()
