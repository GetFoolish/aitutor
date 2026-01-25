import os
from pymongo import MongoClient
from bson import ObjectId
import json
import re

uri = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ai_tutor']

def collect_all_hashes():
    # Broader search for Maxwell-Boltzmann content
    similar = db.scraped_questions.find({'question.content': {'$regex': 'Maxwell|Boltzmann|distribution of speeds', '$options': 'i'}})
    
    unique_hashes = set()
    questions_count = 0
    for q in similar:
        questions_count += 1
        data_str = str(q)
        found = re.findall(r'ka-perseus-graphie/([0-9a-f]+)', data_str)
        unique_hashes.update(found)
            
    print(f"Total questions found: {questions_count}")
    print(f"Total unique hashes: {len(unique_hashes)}")
    
    # Dump mappings for a few from different sets
    # We already have mapping for most.
    # Let's just list all questions and their hashes to see if they follow the same role structure.
    
if __name__ == "__main__":
    collect_all_hashes()
