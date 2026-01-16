import os
import sys
from pymongo import MongoClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def debug_search():
    collection = mongo_db.scraped_questions
    
    # 1. 69324cd9 Forest
    FIXED_PATH = "/fixed_graphs/question_69324cd9_forest.png"
    query_forest = {"question.widgets.image 1.options.backgroundImage.url": FIXED_PATH}
    docs = list(collection.find(query_forest))
    print(f"Forest query '{FIXED_PATH}' found: {len(docs)}")
    if len(docs) > 0:
        print(f"Sample ID: {docs[0]['_id']}")

    # 2. Trig Tables
    # Try a broader regex
    query_trig = {"question.content": {"$regex": "Angle \\|.*55\\degree", "$options": "i"}}
    docs_trig = list(collection.find(query_trig))
    print(f"Trig query found: {len(docs_trig)}")
    if len(docs_trig) > 0:
        print(f"Sample ID: {docs_trig[0]['_id']}")
        print("Sample content snippet:")
        content = docs_trig[0]['question']['content']
        start = content.find("Angle |")
        print(content[start:start+100])

    # 3. 6933fab0 Spacing
    query_space = {"question.content": {"$regex": "\\$ \\[\\[", "$options": "i"}}
    docs_space = list(collection.find(query_space))
    print(f"Space query found: {len(docs_space)}")
    if len(docs_space) > 0:
        print(f"Sample ID: {docs_space[0]['_id']}")
        print(f"Snippet: {docs_space[0]['question']['content'][:100]}")

if __name__ == "__main__":
    debug_search()
