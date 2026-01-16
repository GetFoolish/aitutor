import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_duplicate_captions():
    collection = mongo_db.scraped_questions
    ids = [
        "692fb4b87e334152c5f474df", "6930110aebf6442f98aa9763", "69302897046cc6e7b0047c73",
        "6930763d73cb28d3e4ce429d", "69311a24e85464acc62b5426", "6931470313b91b1a23d2b480",
        "69318c0fa589551921171940", "6931df037be5c6b2e29cc928", "693215bc33f9a4d79a006535",
        "69324cd92e5f91c2481807bc", "6932856c1a6b9ad706c7daa8", "6932b74ecf05997b77546db2",
        "69335eb546bd2cf873ae9da7", "69340807928d27211812264d", "6934c71764942dd77a1123f8",
        "693539fae61eddfd0c726628", "6935731d2a2c00b355a230e3", "6935ac54541cdb343633e03c",
        "6935e54b35efbaf0a785d2a7", "69365fa035282d2b128d1e65", "6936991c5ec39674620d0114"
    ]
    
    caption_text = "Tropical moist broadleaf forests biome near Cairns, Australia"
    
    for qid in ids:
        doc = collection.find_one({"_id": ObjectId(qid)})
        if not doc: continue
        
        content = doc.get('question', {}).get('content', '')
        if caption_text in content:
            print(f"ID {qid}: Caption found in CONTENT")
            # Print a snippet around the match
            idx = content.find(caption_text)
            print(f"Snippet: {content[max(0, idx-50):idx+len(caption_text)+50]}")
        else:
            print(f"ID {qid}: No duplicate caption in content")

if __name__ == "__main__":
    find_duplicate_captions()
