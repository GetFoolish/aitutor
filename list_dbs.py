import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)

try:
    print("Listing all databases in cluster...")
    dbs = client.list_database_names()
    print(f"Databases: {dbs}")
except Exception as e:
    print(f"Error: {e}")
