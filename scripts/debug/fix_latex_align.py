
import os
import sys
import re
from bson import ObjectId

# Add project root to path for shared imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_latex_align():
    snippet = "These are the component forms of vectors"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Found {len(docs)} documents to fix.")
    
    count = 0
    for doc in docs:
        content = doc.get('question', {}).get('content', '')
        
        # Pattern: $\begin{align} ... \end{align}$
        # We want to replace it with $$\begin{aligned} ... \end{aligned}$$
        # Note: We also handle the double backslashes in the original content
        
        new_content = re.sub(
            r'\$\\begin{align}(.*?)\\end{align}\$',
            r'$$\\begin{aligned}\1\\end{aligned}$$',
            content,
            flags=re.DOTALL
        )
        
        if new_content != content:
            mongo_db.scraped_questions.update_one(
                {"_id": doc['_id']},
                {"$set": {"question.content": new_content}}
            )
            print(f"Updated content for: {doc['_id']}")
            count += 1
            
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    fix_latex_align()
