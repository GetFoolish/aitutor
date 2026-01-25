import argparse
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def main():
    parser = argparse.ArgumentParser(description='Search for questions in MongoDB')
    parser.add_argument('--id', type=str, help='Search by question ID')
    parser.add_argument('--query', type=str, help='Search by content regex')
    args = parser.parse_args()

    if args.id:
        print(f"SEARCHING FOR ID: {args.id}")
        doc = mongo_db.scraped_questions.find_one({"_id": args.id})
        if not doc:
            # Try ObjectId if it's a valid hex string
            try:
                from bson import ObjectId
                doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(args.id)})
            except:
                pass
        
        if doc:
            print(f"FOUND QUESTION:")
            print(f"ID: {doc['_id']}")
            print(f"Title: {doc.get('title', 'N/A')}")
            print("-" * 40)
            print("CONTENT:")
            print(doc.get('question', {}).get('content', 'NO CONTENT'))
            print("-" * 40)
            print("WIDGETS:")
            import json
            widgets = doc.get('question', {}).get('widgets', {})
            for name, data in widgets.items():
                print(f"--- Widget: {name} ---")
                print(json.dumps(data, indent=2))
            
            print("-" * 40)
            print("HINTS:")
            hints = doc.get('hints', [])
            if not hints and 'question' in doc:
                hints = doc.get('question', {}).get('hints', [])
            
            for i, hint in enumerate(hints):
                print(f"--- Hint {i+1} ---")
                print(hint.get('content', 'NO CONTENT'))
        else:
            print("Question not found.")
    else:
        SEARCH_TERM = args.query or "[[☃ interactive-graph"
        print(f"SEARCHING FOR: {SEARCH_TERM} questions")
        results = mongo_db.scraped_questions.find({
            "question.content": {"$regex": SEARCH_TERM.replace("[", "\\["), "$options": "i"}
        }).limit(5)

        for doc in results:
            print(f"ID: {doc['_id']} | Title: {doc.get('title', 'N/A')}")

if __name__ == "__main__":
    main()
