from managers.mongodb_manager import mongo_db

def find_specific_limit():
    print("Searching for '\\lim_{x\\to6'...")
    # Regex escape: \ is special in python string AND regex
    # We want matches for \lim_{x\to6
    # Regex: \\lim_\{x\\to6
    
    cursor = mongo_db.scraped_questions.find({
        "question.content": {"$regex": "\\\\lim_\{x\\\\to6"}
    })
    
    for q in cursor:
        print(f"Question ID: {q['_id']}")
        content = q['question']['content']
        # Find the text
        idx = content.find(r"\lim_{x\to6")
        start = max(0, idx - 10)
        end = min(len(content), idx + 50)
        print(f"Snippet: >{content[start:end]}<")
        
        # Check if wrapped in backticks
        if "`" in content[start:end]:
            print("ALERT: Backticks detected near match!")

if __name__ == "__main__":
    find_specific_limit()
