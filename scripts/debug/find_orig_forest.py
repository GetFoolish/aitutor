import os
import sys
from pymongo import MongoClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_original_url():
    # Only search in documents that I HAVEN'T updated to /fixed_graphs/
    query = {
        "$and": [
             {"question.widgets.image 1.options.backgroundImage.url": {"$regex": "e66dad0513ef84779a581b301c3403a3dea810c3"}},
             {"question.widgets.image 1.options.backgroundImage.url": {"$not": {"$regex": "/fixed_graphs/"}}}
        ]
    }
    
    doc = mongo_db.scraped_questions.find_one(query)
    if doc:
        print("FOUND ORIGINAL:")
        print(doc['question']['widgets']['image 1']['options']['backgroundImage']['url'])
    else:
        # If all were updated, searching for ANY that have the forest in the URL name (maybe others exist)
        print("Not found in non-fixed. Searching for all with hash...")
        doc = mongo_db.scraped_questions.find_one({"question.widgets.image 1.options.backgroundImage.url": {"$regex": "e66dad0513ef84779a581b301c3403a3dea810c3"}})
        if doc:
             print("FOUND:")
             print(doc['question']['widgets']['image 1']['options']['backgroundImage']['url'])
        else:
             print("No document found with that hash.")

if __name__ == "__main__":
    find_original_url()
