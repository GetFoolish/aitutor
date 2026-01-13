import json
from managers.mongodb_manager import mongo_db
from bson import ObjectId

def inspect():
    q_id = '69332dbf42728321ec258a4d'
    q = mongo_db.scraped_questions.find_one({'_id': ObjectId(q_id)})
    
    if q:
        print(f"Found question {q_id}")
        # Save to file
        with open('squirrel_question_dump.json', 'w') as f:
            # Helper for ObjectId serialization
            def default(o):
                if isinstance(o, ObjectId):
                    return str(o)
                return str(o)
            
            json.dump(q, f, indent=2, default=default)
        print("Saved to squirrel_question_dump.json")
    else:
        print(f"Question {q_id} not found")

if __name__ == "__main__":
    inspect()
