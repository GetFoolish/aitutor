
import os
import sys
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def fix_all_6932bfa5_variants():
    # The unique content signature
    TARGET_SUBSTRING = "f(t)=\\dfrac{t}{t-8}"
    
    # We want to replace the broken align environment with discrete lines
    # Problematic: $\begin{align} &f(t)=\dfrac{t}{t-8} \\\\ &h(t)=-2t \end{align}$
    # Correct: $f(t)=\dfrac{t}{t-8}$\n\n$h(t)=-2t$
    
    query = {
        "question.content": {"$regex": "f\\(t\\)=\\\\dfrac\\{t\\}\\{t-8\\}"}
    }
    
    print(f"Searching for questions containing: {TARGET_SUBSTRING}")
    results = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(results)} questions to fix.")
    
    count = 0
    for doc in results:
        qid = doc['_id']
        content = doc['question']['content']
        
        # Check if it matches the pattern we expect
        if "\\begin{align}" in content:
            print(f"Processing question {qid}...")
            
            # Simple string replacement for this specific case
            new_content = content.replace("$\\begin{align}", "")
            new_content = new_content.replace("\\end{align}$", "")
            new_content = new_content.replace("&f(t)=\\dfrac{t}{t-8}", "$f(t)=\\dfrac{t}{t-8}$")
            new_content = new_content.replace("\\\\", "\n\n")
            new_content = new_content.replace("&h(t)=-2t", "$h(t)=-2t$")
            
            # Clean up extra newlines if needed
            new_content = new_content.strip()
            
            # Reconstruct slightly to ensure spacing
            # Expected result:
            # $f(t)=\dfrac{t}{t-8}$
            #
            # $h(t)=-2t$
            # 
            # **Evaluate.**
            # ...
            
            if new_content != content:
                mongo_db.scraped_questions.update_one(
                    {"_id": qid},
                    {"$set": {"question.content": new_content}}
                )
                print(f"  Fixed content for {qid}")
                count += 1
            else:
                print(f"  Content matches but replacement failed? {qid}")
        else:
            print(f"  Skipping {qid}, pattern not matched exactly.")

    print(f"Finished. Total updated: {count}")

if __name__ == "__main__":
    fix_all_6932bfa5_variants()
