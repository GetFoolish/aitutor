
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_fixed_similar():
    # Look for questions with the same content pattern but with /fixed_graphs/ in radio choices
    # This would indicate they've been fixed
    
    # First, let's check if any of the 14 variants have been fixed
    variant_ids = [
        "6930bbcc7fa3741ee33a3c17",
        "693139a44d21167d6d552f20",
        "6931a55d84609b1e86beccf6",
        "69327ada8dc997b72646c694",
        "69329763a627ab2be37e6bf0",
        "6932ea04488c4a5c22f22f5c",
        "6933056ad8006a4430ca39e9",
        "693350f918bcab85650eedd8",
        "6933bd8fcd077787e27dc86a",
        "6934a35283a352bc91b80e48",
        "69350b9e4a3e2f377c9242bc",
        "69367075700579bf9cb92daa",
        "69372708f24b2a7955fb0916",
        "693751e5150db826a8c256a3"
    ]
    
    for vid in variant_ids:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(vid)})
        if not doc:
            continue
            
        widgets = doc.get('question', {}).get('widgets', {})
        if 'radio 1' in widgets:
            choices = widgets['radio 1'].get('options', {}).get('choices', [])
            for i, choice in enumerate(choices):
                content = choice.get('content', '')
                if '/fixed_graphs/' in content:
                    print(f"FOUND FIXED VERSION: {vid}")
                    print(f"Choice {i+1}: {content}")
                    return vid, content
                    
    print("No fixed version found among variants.")
    return None, None

if __name__ == "__main__":
    find_fixed_similar()
