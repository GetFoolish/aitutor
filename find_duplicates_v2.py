
import sys
import os

# Add paths to find managers and shared
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'services', 'athenaAPI'))

# Import mongo_db
from managers.mongodb_manager import mongo_db

def find_duplicates():
    search_string = "g(b)=5b-9"
    print(f"Searching for questions containing: '{search_string}'")
    
    # Direct MongoDB query
    # Using regex for content search (plaintext)
    query = {"question.content": {"$regex": search_string, "$options": "i"}}
    
    cursor = mongo_db.scraped_questions.find(query, {"_id": 1, "question.content": 1, "slug": 1})
    
    results = list(cursor)
    print(f"Found {len(results)} duplicates.")
    
    for doc in results:
        qid = str(doc.get('_id'))
        slug = doc.get('slug', 'no-slug')
        print(f" - ID: {qid} | Slug: {slug}")

if __name__ == "__main__":
    try:
        find_duplicates()
    except Exception as e:
        print(f"Error: {e}")
