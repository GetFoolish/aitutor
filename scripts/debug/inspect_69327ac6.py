
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def inspect_69327ac6():
    qid = "69327ac68dc997b72646c690"
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        
    if not doc:
        print(f"Question {qid} not found.")
        return

    content = doc.get('question', {}).get('content', '')
    print("--- CONTENT START ---")
    print(content)
    print("--- CONTENT END ---")
    
    widgets = doc.get('question', {}).get('widgets', {})
    if 'image 1' in widgets:
        img_opt = widgets['image 1'].get('options', {})
        print(f"\nImage 1 URL: {img_opt.get('backgroundImage', {}).get('url')}")
        print(f"Image 1 Alt: {img_opt.get('alt')}")

    # Find variants
    # Use the first 50 chars of content to find variants
    snippet = content[:50]
    escaped_snippet = re.escape(snippet)
    print(f"\nSearching for variants with snippet: {snippet}")
    variants = list(mongo_db.scraped_questions.find({"question.content": {"$regex": escaped_snippet}}))
    print(f"Found {len(variants)} variants.")
    for v in variants:
        v_qid = v['_id']
        v_img = v.get('question', {}).get('widgets', {}).get('image 1', {}).get('options', {}).get('backgroundImage', {}).get('url')
        print(f"ID: {v_qid} | Image: {v_img}")

if __name__ == "__main__":
    inspect_69327ac6()
