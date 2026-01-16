import os
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def diagnose():
    collection = mongo_db.scraped_questions
    print(f"DB: {collection.database.name}, Collection: {collection.name}")
    
    # 1. 69324cd9 Forest
    FIXED_PATH = "/fixed_graphs/question_69324cd9_forest.png"
    q_fixed = {"question.widgets.image 1.options.backgroundImage.url": FIXED_PATH}
    fixed_count = collection.count_documents(q_fixed)
    print(f"Count with FIXED URL '{FIXED_PATH}': {fixed_count}")
    
    ORIG_HASH = "e66dad0513ef84779a581b301c3403a3dea810c3"
    q_orig = {"question.widgets.image 1.options.backgroundImage.url": {"$regex": ORIG_HASH}}
    orig_count = collection.count_documents(q_orig)
    print(f"Count with ORIG HASH regex: {orig_count}")

    # 2. Trig
    print("\n--- Trig Tests ---")
    # Exact target string from previous diagnostic: 'Angle | $55\\degree$ | $65\\degree$ | $75\\degree$'
    TARGET_HEAD = r"Angle | $55\degree$ | $65\degree$ | $75\degree$"
    q_trig_exact = {"question.content": {"$regex": TARGET_HEAD.replace("|", r"\|").replace("$", r"\$").replace("\\", r"\\")}}
    print(f"Count with EXACT trig header regex: {collection.count_documents(q_trig_exact)}")
    
    # Try just the degrees
    q_trig_deg = {"question.content": {"$regex": r"55\\degree.*65\\degree"}}
    print(f"Count with '55\\degree.*65\\degree': {collection.count_documents(q_trig_deg)}")

    # 3. Spacing
    # Let's check a known ID for the spacing issue if possible.
    # The summary says 6933fab0.
    qid_space = "6933fab0ced92484ab84cedb" # Example ID from previous session history
    try:
        doc_space = collection.find_one({"_id": ObjectId(qid_space)})
        if doc_space:
            print(f"\nDocument {qid_space} found.")
            content = doc_space['question']['content']
            import reprlib
            print(f"Content repr: {repr(content)}")
            print(f"Contains '$ [['? {'$ [[' in content}")
    except:
        pass

if __name__ == "__main__":
    diagnose()
