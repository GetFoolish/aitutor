from managers.mongodb_manager import mongo_db
import sys

def dump_latex():
    print("Dumping questions with \\displaystyle...")
    
    cursor = mongo_db.scraped_questions.find({
        "question.content": {"$regex": "\\\\displaystyle"}
    })
    
    with open("dump_latex.txt", "w", encoding="utf-8") as f:
        count = 0
        for q in cursor:
            count += 1
            f.write(f"=== [{count}] ID: {q['_id']} ===\n")
            f.write(q['question']['content'])
            f.write("\n\n")
            
    print(f"Dumped {count} questions to dump_latex.txt")

if __name__ == "__main__":
    dump_latex()
