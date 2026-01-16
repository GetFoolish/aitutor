import os
import sys
from pymongo import MongoClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def test_connection():
    try:
        count = mongo_db.scraped_questions.count_documents({})
        print(f"Connected! Total questions: {count}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
