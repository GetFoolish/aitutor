import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

MONGO_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME') or 'ai_tutor'

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

print(f"Collections in {DB_NAME}:")
for coll in db.list_collection_names():
    print(f"- {coll}")
