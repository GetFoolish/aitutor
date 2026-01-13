from managers.mongodb_manager import mongo_db
import re

def find_exact_limit():
    print("Searching for limit x->6...")
    
    # Text to search: "6^{-}"
    # Regex: 6\^\{-?\}
    
    cursor = mongo_db.scraped_questions.find({
        "question.content": {"$regex": "6\\^\\{-?\\}"}
    })
    
    count = 0
    for q in cursor:
        count += 1
        print(f"[{count}] Question ID: {q['_id']}")
        content = q['question']['content']
        print(f"Content Snippet: {content[:200]}...")
        
        # Check if wrapped in backticks
        if "`" in content:
            print("  ALERT: Backticks found in content!")
            # Find location of backticks
            start = content.find("`")
            print(f"  Backtick context: ...{content[start:start+50]}...")
            
        # Check for \displaystyle
        if "\\displaystyle" in content:
            idx = content.find("\\displaystyle")
            print(f"  \\displaystyle context: ...{content[max(0, idx-20):idx+50]}...")

    if count == 0:
        print("No matches for 6^{-}")
        
    # Search for "What appears to be the value of" + backticks
    print("\nSearching for backticked 'What appears'...")
    cursor2 = mongo_db.scraped_questions.find({
        "question.content": {"$regex": "`What appears"}
    })
    for q in cursor2:
       print(f"Backticked Question: {q['_id']}")

if __name__ == "__main__":
    find_exact_limit()
