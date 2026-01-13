from managers.mongodb_manager import mongo_db

def find_specific_qquad():
    print("Searching for 'Subtract' and '\\qquad' in HINTS...")
    
    cursor = mongo_db.scraped_questions.find({
        "hints.content": {"$regex": "Subtract.*\\\\qquad", "$options": "s"}
    })
    
    count = 0
    for q in cursor:
        count += 1
        print(f"[{count}] Question ID: {q['_id']}")
        for h in q.get('hints', []):
            if "Subtract" in h['content'] and "\\qquad" in h['content']:
                print(f"  Match in Hint: {h['content'][:500]}")

if __name__ == "__main__":
    find_specific_qquad()
