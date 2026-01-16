
import os
import sys
import json
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def find_asterisks():
    qid = "69324cd92e5f91c2481807bc"
    doc = mongo_db.scraped_questions.find_one({"_id": qid})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    
    if not doc:
        print("Not found")
        return
        
    # Search for "**" in everything
    def search_dict(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                search_dict(v, f"{path}.{k}")
        elif isinstance(d, list):
            for i, v in enumerate(d):
                search_dict(v, f"{path}[{i}]")
        elif isinstance(d, str):
            if "**" in d:
                print(f"Found ** at {path}: {d}")

    search_dict(doc)

if __name__ == "__main__":
    find_asterisks()
