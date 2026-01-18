
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def debug_search():
    old_url = "web+graphie://cdn.kastatic.org/ka-perseus-graphie/398b806e971ebf7c10dce6fbbf789fe4dfa9a0a9"
    qid = "69360b810aabe66864660c1a"
    
    # Try direct match for the known QID
    doc = mongo_db.scraped_questions.find_one({
        "_id": ObjectId(qid),
        "question.widgets.image 1.options.backgroundImage.url": old_url
    })
    print(f"Direct match found: {doc is not None}")
    
    # Let's try to find all by searching for the hash string in the field
    results = list(mongo_db.scraped_questions.find({"$or": [
        {"question.widgets.image 1.options.backgroundImage.url": old_url},
        {"question.widgets.image 2.options.backgroundImage.url": old_url},
        {"question.widgets.image 3.options.backgroundImage.url": old_url}
    ]}))
    print(f"Found {len(results)} variants via direct widget path.")

if __name__ == "__main__":
    debug_search()
