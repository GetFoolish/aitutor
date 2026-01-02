from managers.mongodb_manager import mongo_db
from bson import ObjectId
import json

def get_db_question(qid):
    try:
        doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(qid)})
        if not doc:
            print(f"Question {qid} not found")
            return
        
        # Clean up ObjectId for printing
        doc['_id'] = str(doc['_id'])
        print(json.dumps(doc, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # ID from screenshot
    get_db_question("691c6be841372912898cd488")
