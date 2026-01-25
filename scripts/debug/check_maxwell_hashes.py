import os
from pymongo import MongoClient
from bson import ObjectId
import json

uri = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ai_tutor']

def check_hashes(ids):
    results = {}
    for qid in ids[:10]: # Check first 10
        q = db.scraped_questions.find_one({'_id': ObjectId(qid)})
        if q:
            # Look for graphie hashes in content and widgets
            data_str = str(q)
            hashes = set()
            import re
            found = re.findall(r'ka-perseus-graphie/([0-9a-f]+)', data_str)
            hashes.update(found)
            results[qid] = sorted(list(hashes))
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    ids = ['692fb8537490ab0b8d10d2fb', '692fb8587490ab0b8d10d2fc', '692ff6ce55a316d766a3be8b', '6933cda083a8bc4c63d261ed']
    check_hashes(ids)
