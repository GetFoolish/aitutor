
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

# All variant IDs (excluding the already fixed one: 693751e5150db826a8c256a3)
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
    "6934a35283a352bc91b80e48",  # The one the user reported
    "69350b9e4a3e2f377c9242bc",
    "69367075700579bf9cb92daa",
    "69372708f24b2a7955fb0916",
    # "693751e5150db826a8c256a3"  # Already fixed, excluded
]

# The fixed solution (from 693751e5)
FIXED_CHOICE_1 = "![Bar chart](/fixed_graphs/bar_chart_choice_1_693751e5.png)"
FIXED_CHOICE_2 = "![Bar chart](/fixed_graphs/bar_chart_choice_2_693751e5.png)"

def apply_fix():
    count = 0
    for qid in variant_ids:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(qid)})
        if not doc:
            doc = mongo_db.scraped_questions.find_one({"_id": qid})
            
        if not doc:
            print(f"Not found: {qid}")
            continue
            
        widgets = doc.get('question', {}).get('widgets', {})
        if 'radio 1' not in widgets:
            print(f"No radio widget in {qid}")
            continue
            
        choices = widgets['radio 1']['options']['choices']
        
        # Check if already fixed
        if '/fixed_graphs/' in choices[0].get('content', ''):
            print(f"Already fixed: {qid}")
            continue
            
        # Apply the fix
        if len(choices) >= 2:
            choices[0]['content'] = FIXED_CHOICE_1
            choices[1]['content'] = FIXED_CHOICE_2
            
            # Update in database
            mongo_db.scraped_questions.update_one(
                {"_id": doc["_id"]},
                {"$set": {"question.widgets.radio 1.options.choices": choices}}
            )
            print(f"Updated: {qid}")
            count += 1
        else:
            print(f"Unexpected number of choices in {qid}: {len(choices)}")
                
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    apply_fix()
