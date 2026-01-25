
import json
from pymongo import MongoClient
import sys

# Connect to MongoDB
client = MongoClient('mongodb+srv://sherlocked:sherlocked123@cluster0.bbw2k.mongodb.net/athena_db?retryWrites=true&w=majority')
db = client['athena_db']
collection = db['exercises']

question_id = "693643a203d86cedf65fa681"

# Find the question
question = collection.find_one({"id": question_id})

if question:
    print(f"--- Question Data for {question_id} ---")
    # specific fields of interest
    print(f"Type: {question.get('type', 'N/A')}")
    
    question_data = question.get('question_data', {})
    print(json.dumps(question_data, indent=2))
else:
    print(f"Question {question_id} not found.")
