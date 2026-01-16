import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_and_revert():
    collection = mongo_db.scraped_questions
    
    # 1. Revert Forest Image URL for 69324cd9 variants
    print("--- Reverting Forest Image URL for 69324cd9 ---")
    OLD_FOREST_HASH = "e66dad0513ef84779a581b301c3403a3dea810c3"
    ORIG_URL = f"web+graphie://cdn.kastatic.org/ka-perseus-graphie/{OLD_FOREST_HASH}"
    FIXED_PATH = "/fixed_graphs/question_69324cd9_forest.png"
    
    query_forest = {"question.widgets.image 1.options.backgroundImage.url": FIXED_PATH}
    forest_docs = list(collection.find(query_forest))
    print(f"Found {len(forest_docs)} questions to revert forest image URL.")
    
    for doc in forest_docs:
        qid = doc['_id']
        widgets = doc['question'].get('widgets', {})
        if 'image 1' in widgets:
            widgets['image 1']['options']['backgroundImage']['url'] = ORIG_URL
            collection.update_one({"_id": qid}, {"$set": {"question.widgets": widgets}})
            print(f"  Reverted forest URL for {qid}")

    # 2. Fix Trig Table Headers
    print("\n--- Fixing Trigonometry Table Headers ---")
    # Search for "Angle |" followed by degrees in content
    query_trig = {"question.content": {"$regex": "Angle \\| \\$55\\degree\\|", "$options": "i"}}
    trig_docs = list(collection.find(query_trig))
    print(f"Found {len(trig_docs)} potential trig table questions.")
    
    for doc in trig_docs:
        qid = doc['_id']
        content = doc.get('question', {}).get('content', '')
        if "Angle | $55\degree$ | $65\degree$ | $75\degree$" in content:
            new_content = content.replace(
                "Angle | $55\degree$ | $65\degree$ | $75\degree$",
                "Ratio | $55\degree$ | $65\degree$ | $75\degree$"
            )
            collection.update_one({"_id": qid}, {"$set": {"question.content": new_content}})
            print(f"  Fixed trig header for {qid}")

if __name__ == "__main__":
    fix_and_revert()
