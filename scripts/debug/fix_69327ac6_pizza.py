
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

ids = [
    "6930bbbc7fa3741ee33a3c13",
    "693139904d21167d6d552f1c",
    "6931a54684609b1e86beccf2",
    "69327ac68dc997b72646c690",
    "69329751a627ab2be37e6bec",
    "6932e9ee488c4a5c22f22f58",
    "69330556d8006a4430ca39e5",
    "693350e218bcab85650eedd4",
    "6933bd7dcd077787e27dc866",
    "6934a33b83a352bc91b80e44",
    "69350b844a3e2f377c9242b8",
    "69367060700579bf9cb92da6",
    "693726f6f24b2a7955fb0912",
    "693751cd150db826a8c2569f"
]

NEW_IMAGE_URL = "/fixed_graphs/question_69327ac6_pizza.png"

def apply_fix():
    count = 0
    for qid in ids:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
        if not doc:
            doc = mongo_db.scraped_questions.find_one({"_id": qid})
            
        if doc:
            # Update image 1 widget
            mongo_db.scraped_questions.update_one(
                {"_id": doc["_id"]},
                {"$set": {"question.widgets.image 1.options.backgroundImage.url": NEW_IMAGE_URL}}
            )
            print(f"Updated: {doc['_id']}")
            count += 1
        else:
            print(f"Not found: {qid}")
                
    print(f"Total updated: {count}")

if __name__ == "__main__":
    apply_fix()
