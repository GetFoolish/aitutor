
import os
import sys
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def search_variants():
    # Use a part of the text that's unlikely to have quote issues
    snippet = "Sherwood Anderson"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} documents.")
    for d in docs:
        print(f"ID: {d['_id']}, Content snippet: {repr(d['question']['content'][:100])}")

if __name__ == "__main__":
    search_variants()
