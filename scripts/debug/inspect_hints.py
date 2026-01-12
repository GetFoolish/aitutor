import os
import sys
import json
import argparse
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=str, default="6931336e4d21167d6d552e61")
    args = parser.parse_args()
    
    q_id = args.id
    print(f"SEARCHING FOR ID: {q_id}")
    
    collections = ['scraped_questions', 'perseus_questions', 'dash_questions']
    doc = None
    coll_name_found = None
    
    for coll_name in collections:
        coll = mongo_db.db[coll_name]
        # Try as string
        doc = coll.find_one({"_id": q_id})
        if doc: 
            coll_name_found = coll_name
            print(f"FOUND in {coll_name} as string")
            break
        # Try as ObjectId
        try:
            doc = coll.find_one({"_id": ObjectId(q_id)})
            if doc:
                coll_name_found = coll_name
                print(f"FOUND in {coll_name} as ObjectId")
                break
        except:
            pass
            
    if doc:
        # Check standard Perseus structure
        p_item = doc.get('perseusItem', {})
        if not p_item and 'question' in doc:
            p_item = doc # maybe it's already a flattened item
            
        # Print question content and widgets
        print("\n--- QUESTION CONTENT ---")
        q_data = p_item.get('question', {})
        print(f"CONTENT: {q_data.get('content', '')}")
        q_widgets = q_data.get('widgets', {})
        print(f"WIDGETS KEYS: {list(q_widgets.keys())}")
        for wid, wdata in q_widgets.items():
            w_type = wdata.get('type')
            print(f"  > Widget '{wid}': type={w_type}")
            if w_type == 'image' or w_type == 'radio':
                options = wdata.get('options', {})
                print(f"    OPTIONS: {json.dumps(options, indent=2)}")

        p_hints = p_item.get('hints', [])
        
        # If no hints in p_item, check top level
        if not p_hints:
            p_hints = doc.get('hints', [])
            
        print(f"\nFOUND {len(p_hints)} HINTS")
        for i, hint in enumerate(p_hints):
            print(f"\n--- HINT {i+1} ---")
            print(f"CONTENT: {hint.get('content', '')}")
            widgets = hint.get('widgets', {})
            print(f"WIDGETS KEYS: {list(widgets.keys())}")
            for wid, wdata in widgets.items():
                w_type = wdata.get('type')
                print(f"  > Widget '{wid}': type={w_type}")
                if w_type == 'image':
                    options = wdata.get('options', {})
                    print(f"    URL: {options.get('backgroundImage', {}).get('url') or options.get('url')}")
                    print(f"    ALT: {options.get('alt')}")
                    print(f"    OPTIONS: {json.dumps(options, indent=2)}")
    else:
        print("Question not found in searched collections.")

if __name__ == "__main__":
    main()
