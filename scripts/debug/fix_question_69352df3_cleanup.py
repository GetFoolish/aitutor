
import os
import sys
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def cleanup_69352df3_variants():
    # Only target questions that still have "\text{Step" which indicates incomplete replacement
    query = {
        "question.content": {"$regex": "\\\\text\\{Step"}
    }
    
    print(f"Searching for partially fixed questions...")
    try:
        results = list(mongo_db.scraped_questions.find(query))
        print(f"Found {len(results)} questions to cleanup.")
    except Exception as e:
        print(f"DB Search failed: {e}")
        return

    count = 0
    for doc in results:
        qid = doc['_id']
        content = doc['question']['content']
        
        print(f"Processing question {qid}...")
        new_content = content
        
        # Exact strings seen in the failure mode (derived from browser screenshot + hypothesis about braces)
        replacements = [
            # Fix Step 1
            ("\\text{Step 1}&h({7})&=3({7})-11", "\n\n**Step 1**\n$h(7)=3(7)-11$"),
            ("\\text{Step 1}&h(7)&=3(7)-11", "\n\n**Step 1**\n$h(7)=3(7)-11$"), # variant without braces just in case
            
            # Fix Step 3
            ("\\text{Step 3}&f({10})&=-10^2", "\n\n**Step 3**\n$f(10)=-10^2$"),
            ("\\text{Step 3}&f(10)&=-10^2", "\n\n**Step 3**\n$f(10)=-10^2$"),
            
            # Cleanup any remaining table/array artifacts
            ("\\\\", "\n"), 
            ("&", " ") # Remove stray alignment chars
        ]
        
        updated = False
        for old, new in replacements:
            if old in new_content:
                new_content = new_content.replace(old, new)
                updated = True
                
        # Additional cleanup for lines that might be formatted like "&&={10}" -> "$=10$"
        # These might have been missed if they were on new lines
        if "&&={10}" in new_content:
            new_content = new_content.replace("&&={10}", "$=10$")
            updated = True
        
        if "&&=100" in new_content:
            new_content = new_content.replace("&&=100", "$=100$")
            updated = True

        if updated and new_content != content:
            try:
                mongo_db.scraped_questions.update_one(
                    {"_id": qid},
                    {"$set": {"question.content": new_content}}
                )
                print(f"  Fixed content for {qid}")
                count += 1
            except Exception as e:
                 print(f"  Update failed for {qid}: {e}")
        else:
            print(f"  No changes needed (or patterns didn't match) for {qid}")

    print(f"Finished. Total updated: {count}")

if __name__ == "__main__":
    cleanup_69352df3_variants()
