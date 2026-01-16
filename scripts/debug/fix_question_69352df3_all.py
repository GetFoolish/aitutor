
import os
import sys
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def fix_all_69352df3_variants():
    # Target signature strings
    SIGNATURE_1 = "f(n)=-n^2"
    SIGNATURE_2 = "h(n)=3n-11"
    
    # We are looking for questions containing these functions
    query = {
        "question.content": {"$regex": "f\\(n\\)=-n\\^2"}
    }
    
    print(f"Searching for questions containing: {SIGNATURE_1}")
    try:
        results = list(mongo_db.scraped_questions.find(query))
        print(f"Found {len(results)} questions to fix.")
    except Exception as e:
        print(f"DB Search failed: {e}")
        return

    count = 0
    for doc in results:
        qid = doc['_id']
        content = doc['question']['content']
        
        # Verify it has the second function too, to be safe
        if SIGNATURE_2 not in content:
            print(f"Skipping {qid}, missing h(n) signature.")
            continue

        print(f"Processing question {qid}...")
        new_content = content
        
        # 1. Fix the 'align' block
        # Pattern: $\begin{align} &f(n)=-n^2 \\ &h(n)=3n-11 \end{align}$
        if "\\begin{align}" in new_content:
            new_content = new_content.replace("\\begin{align}", "")
            new_content = new_content.replace("\\end{align}", "")
            new_content = new_content.replace("&f(n)=-n^2", "$f(n)=-n^2$")
            new_content = new_content.replace("&h(n)=3n-11", "$h(n)=3n-11$")
            # Replace double backslashes with double newlines
            new_content = new_content.replace("\\\\", "\n\n")
            # Clean up the outer $ and extra spacing
            new_content = new_content.replace("$$", "$").replace("$ $", "$\n\n$")
        
        # 2. Fix the 'array' block (Steps)
        # We will replace the whole array block with formatted markdown
        # It's safer to reconstruct the array part entirely if we match the start
        if "\\begin{array}" in new_content:
            # We'll split the content to isolate the array part if possible, 
            # OR we can do string replacement if the array content is consistent.
            # Given the image, the array content seems standard.
            
            # Let's try to remove the array wrapper and clean up the inside
            # \text{Step 1}&h(7)&=3(7)-11\\ &&={10}\\ \text{Step 2}&(f \circ h)(7) &=f(h(7))\\ &&=f(10)\\ \text{Step 3}&f({10})&=-10^2 \\ &&=100
            
            replacement_map = {
                "\\begin{array}{lrl}": "",
                "\\end{array}": "",
                "\\text{Step 1}&h(7)&=3(7)-11": "**Step 1**\n$h(7)=3(7)-11$",
                "&&={10}": "$=10$",
                "\\text{Step 2}&(f \\circ h)(7) &=f(h(7))": "\n\n**Step 2**\n$(f \\circ h)(7) =f(h(7))$",
                "&&=f(10)": "$=f(10)$",
                "\\text{Step 3}&f({10})&=-10^2": "\n\n**Step 3**\n$f(10)=-10^2$",
                "&&=100": "$=100$"
            }
            
            for old, new in replacement_map.items():
                new_content = new_content.replace(old, new)
                
            # Clean up remaining backslashes from the array rows (\\)
            # We already replaced \\ inside the align block, but array usage might still have them if we didn't catch them all or if they were part of the replacement strings?
            # actually strict replacement above handles the text. The only remaining things are `\\` at end of lines.
            
            # Let's simple-replace the `\\` that are likely left over
            new_content = new_content.replace("\\\\", "\n")
            
            # Clean up potential mess with outer $ signs wrapping the array
            new_content = new_content.replace("$$", "") # If the array was wrapped in $$...$$ or $...$
            
            # Ideally we want:
            # **Step 1**
            # ...
        
        # Consolidated cleanup for any double dollar signs created
        while "$$" in new_content:
            new_content = new_content.replace("$$", "$")
            
        new_content = new_content.strip()

        if new_content != content:
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
            print(f"  No changes needed or regex failed for {qid}")

    print(f"Finished. Total updated: {count}")

if __name__ == "__main__":
    fix_all_69352df3_variants()
