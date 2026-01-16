import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def apply_forest_image_fix():
    collection = mongo_db.scraped_questions
    
    # Target path for the local asset
    LOCAL_PATH = "/fixed_graphs/question_69324cd9_forest.png"
    # The hash to search for to identify duplicates
    ORIG_HASH = "e66dad0513ef84779a581b301c3403a3dea810c3"
    
    # Query for documents with this hash in the image 1 widget
    query = {"question.widgets.image 1.options.backgroundImage.url": {"$regex": ORIG_HASH}}
    docs = list(collection.find(query))
    print(f"Found {len(docs)} documents to update.")
    
    updated_count = 0
    for doc in docs:
        widgets = doc.get('question', {}).get('widgets', {})
        if 'image 1' in widgets:
            widgets['image 1']['options']['backgroundImage']['url'] = LOCAL_PATH
            # Also update search indexing content if it stores the URL there, 
            # though usually it's just in the widget options for this renderer.
            
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"question.widgets": widgets}}
            )
            updated_count += 1
            print(f"Updated document: {doc['_id']}")
            
    print(f"\nSuccessfully updated {updated_count} documents with local forest image path.")

if __name__ == "__main__":
    apply_forest_image_fix()
