from managers.mongodb_manager import mongo_db

def find_qquad_any():
    print("Searching for '\\qquad' in HINTS...")
    
    cursor = mongo_db.scraped_questions.find({
        "hints.content": {"$regex": "\\\\qquad"}
    })
    
    count = 0
    for q in cursor:
        count += 1
        print(f"[{count}] Question ID: {q['_id']}")
        for h in q.get('hints', []):
            if "\\qquad" in h['content']:
                print(f"  Hint: {h['content'][:200]}...")

if __name__ == "__main__":
    find_qquad_any()
