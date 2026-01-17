
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def extract_fixed_solution():
    fixed_id = "693751e5150db826a8c256a3"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(fixed_id)})
    
    if not doc:
        print("Fixed version not found.")
        return
        
    widgets = doc.get('question', {}).get('widgets', {})
    if 'radio 1' in widgets:
        choices = widgets['radio 1'].get('options', {}).get('choices', [])
        print(f"Fixed version has {len(choices)} choices:\n")
        for i, choice in enumerate(choices):
            content = choice.get('content', '')
            print(f"=== Choice {i+1} ===")
            print(content)
            print()

if __name__ == "__main__":
    extract_fixed_solution()
