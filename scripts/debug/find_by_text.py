from managers.mongodb_manager import mongo_db
import json

def find_by_text(text):
    results = list(mongo_db.scraped_questions.find({"question.content": {"$regex": text, "$options": "i"}}))
    print(f"Found {len(results)} results")
    for r in results:
        r['_id'] = str(r['_id'])
        print(json.dumps(r, indent=2))

if __name__ == "__main__":
    find_by_text("Which expression is equivalent to 8")
