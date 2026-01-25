import os
import json
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def dump_question(question_id):
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
    
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    # Try to find by questionId (the string ID)
    question = db.scraped_questions.find_one({"questionId": question_id})
    
    if not question:
        # Try finding by ObjectId hex if they passed the internal _id
        try:
            question = db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
            
    if not question:
        print(f"Question {question_id} not found")
        return

    # Extract assessmentData
    assessment_data = question.get('assessmentData', {})
    item_data_str = assessment_data.get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
    
    if item_data_str:
        item_data = json.loads(item_data_str)
        print(json.dumps(item_data, indent=2))
    else:
        print("No itemData found")

if __name__ == "__main__":
    dump_question("6931a65284609b1e86becd11")
