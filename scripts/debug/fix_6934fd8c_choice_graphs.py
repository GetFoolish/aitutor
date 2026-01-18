
import os
import sys
import re
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def fix_choice_graphs_6934fd8c():
    fixes = {
        "b3db47b21c9e3744dbf2af4aa0f80e751c2ed590": "/fixed_graphs/question_6934fd8c_choice_0_100.png",
        "e4bf0c1da327b6e8f958112c6dd5612f60ef0a92": "/fixed_graphs/question_6934fd8c_choice_1_20.png",
        "5700064c4fdc1370631c69d2181568a80da6649d": "/fixed_graphs/question_6934fd8c_choice_2_10.png"
    }
    
    variant_ids = [
        "69339e542695081ba20ca038",
        "6933a4102695081ba20ca0d6",
        "69341344948fc265153f457d",
        "693415af948fc265153f45c1",
        "69344d484736cfd74285faec",
        "69348656e9d6a82e390ae4d9",
        "6934fd8cb93b2fcaf1995ba5",
        "69356ec22a2c00b355a2305c",
        "693572a22a2c00b355a230d2"
    ]
    
    count = 0
    for qid_str in variant_ids:
        qid = ObjectId(qid_str)
        doc = mongo_db.scraped_questions.find_one({"_id": qid})
        if not doc:
            print(f"Question {qid_str} not found.")
            continue
            
        widgets = doc.get('question', {}).get('widgets', {})
        radio_widget = widgets.get('radio 1', {})
        if not radio_widget:
            print(f"Radio widget not found in {qid_str}")
            continue
            
        choices = radio_widget.get('options', {}).get('choices', [])
        updated = False
        
        for choice in choices:
            content = choice.get('content', '')
            for broken_hash, fixed_path in fixes.items():
                if broken_hash in content:
                    choice['content'] = content.replace(f"web+graphie://cdn.kastatic.org/ka-perseus-graphie/{broken_hash}", fixed_path)
                    updated = True
                    
        if updated:
            mongo_db.scraped_questions.update_one(
                {"_id": qid},
                {"$set": {"question.widgets.radio 1.options.choices": choices}}
            )
            print(f"Updated choice graphs for: {qid_str}")
            count += 1
            
    print(f"\nTotal updated: {count}")

if __name__ == "__main__":
    fix_choice_graphs_6934fd8c()
