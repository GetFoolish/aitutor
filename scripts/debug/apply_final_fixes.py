import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def final_fix():
    collection = mongo_db.scraped_questions
    
    # 1. Trig Table Fix (Angle -> Ratio)
    # Target line: 'Angle | $55\degree$ | $65\degree$ | $75\degree$'
    print("--- Fixing Trigonometry Table Headers ---")
    # Using a broader regex to find the tables
    query_trig = {"question.content": {"$regex": r"Angle.*55\\degree.*65\\degree", "$options": "i"}}
    trig_docs = list(collection.find(query_trig))
    print(f"Found {len(trig_docs)} questions to update.")
    
    trig_count = 0
    for doc in trig_docs:
        content = doc.get('question', {}).get('content', '')
        if "Angle" in content and "55\degree" in content:
            # Replace exactly the header line
            new_content = content.replace("Angle | $55\degree$", "Ratio | $55\degree$")
            # Also try without spaces if some variants differ
            if new_content == content:
                new_content = content.replace("Angle|$55\degree$", "Ratio|$55\degree$")
            
            if new_content != content:
                collection.update_one({"_id": doc["_id"]}, {"$set": {"question.content": new_content}})
                trig_count += 1
    print(f"Updated {trig_count} trigonometry questions.")

    # 2. Revert Forest Image (if any still exist)
    print("\n--- Checking for forest image URL reversion ---")
    FIXED_PATH = "/fixed_graphs/question_69324cd9_forest.png"
    ORIG_URL = "web+graphie://cdn.kastatic.org/ka-perseus-graphie/e66dad0513ef84779a581b301c3403a3dea810c3"
    
    query_forest = {"question.widgets.image 1.options.backgroundImage.url": FIXED_PATH}
    forest_docs = list(collection.find(query_forest))
    print(f"Found {len(forest_docs)} questions with fixed forest URL.")
    
    forest_reverted = 0
    for doc in forest_docs:
        widgets = doc['question'].get('widgets', {})
        if 'image 1' in widgets:
            widgets['image 1']['options']['backgroundImage']['url'] = ORIG_URL
            collection.update_one({"_id": doc["_id"]}, {"$set": {"question.widgets": widgets}})
            forest_reverted += 1
    print(f"Reverted {forest_reverted} forest image URLs.")

    # 3. Spacing Fix (for juice boxes and others)
    print("\n--- Checking for spaced dollar sign fix ---")
    # Looking for "$ [[" and replacing with "$[["
    query_space = {"question.content": {"$regex": r"\$ \[\["}}
    space_docs = list(collection.find(query_space))
    print(f"Found {len(space_docs)} questions with spacing issue.")
    
    space_count = 0
    for doc in space_docs:
        content = doc.get('question', {}).get('content', '')
        if "$ [[" in content:
            new_content = content.replace("$ [[", "$[[")
            collection.update_one({"_id": doc["_id"]}, {"$set": {"question.content": new_content}})
            space_count += 1
    print(f"Fixed spacing for {space_count} questions.")

if __name__ == "__main__":
    final_fix()
