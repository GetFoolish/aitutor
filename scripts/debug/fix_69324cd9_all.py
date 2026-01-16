
import os
import sys
import json
from bson.objectid import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from managers.mongodb_manager import mongo_db

def fix_69324cd9_variants():
    # New local paths
    NEW_FOREST = "/fixed_graphs/question_69324cd9_forest.png"
    NEW_GRAPH_1 = "/fixed_graphs/question_69324cd9_graph_1.png"
    NEW_GRAPH_2 = "/fixed_graphs/question_69324cd9_graph_2.png"
    NEW_GRAPH_3 = "/fixed_graphs/question_69324cd9_graph_3.png"
    
    # Signatures of choices to replace
    # Choice 0 (Incorrect): peaked temp at 18, low precip
    SIG_0 = "00e9fa2d0d6d0c01ef25b2b766cd7deb782ed660"
    # Choice 1 (Incorrect): low precip June-Sept
    SIG_1 = "baea72fc27c75c2804f8a2f19527b3cdd066b3cd"
    # Choice 2 (Correct): High precip year-round
    SIG_2 = "68459e4571971b1d67aff15aa18f4f5d14ef3b9b"

    # Search for all variants using the main forest image or these graphs
    query = {
        "$or": [
            {"question.widgets.image 1.options.backgroundImage.url": {"$regex": "e66dad0513ef84779a581b301c3403a3dea810c3"}},
            {"question.widgets.radio 1.options.choices.content": {"$regex": SIG_2}}
        ]
    }
    
    print("Searching for questions...")
    try:
        results = list(mongo_db.scraped_questions.find(query))
        print(f"Found {len(results)} questions.")
    except Exception as e:
        print(f"Error: {e}")
        return

    count = 0
    for doc in results:
        qid = doc['_id']
        print(f"Processing {qid}...")
        
        widgets = doc['question'].get('widgets', {})
        updated = False
        
        # 1. Fix Image 1
        if 'image 1' in widgets:
            opts = widgets['image 1']['options']
            # Replace URL
            if "fixed_graphs" not in opts['backgroundImage']['url']:
                opts['backgroundImage']['url'] = NEW_FOREST
                print("  Updated forest image URL")
                updated = True
                
            # Remove ** or * from title/caption
            for field in ['title', 'caption']:
                val = opts.get(field, '')
                if val:
                    # Remove both ** and * just to be sure
                    new_val = val.replace("**", "").replace("*", "").strip()
                    if new_val != val:
                        print(f"  Cleaned {field}: '{val}' -> '{new_val}'")
                        opts[field] = new_val
                        updated = True
        
        # 2. Fix Radio Choices
        if 'radio 1' in widgets:
            choices = widgets['radio 1']['options']['choices']
            for i, choice in enumerate(choices):
                content = choice.get('content', '')
                if SIG_0 in content:
                    choice['content'] = f"![Graph Choice 0]({NEW_GRAPH_2})"
                    print(f"  Updated Choice {i} graph (SIG_0)")
                    updated = True
                elif SIG_1 in content:
                    choice['content'] = f"![Graph Choice 1]({NEW_GRAPH_1})"
                    print(f"  Updated Choice {i} graph (SIG_1)")
                    updated = True
                elif SIG_2 in content:
                    choice['content'] = f"![Graph Choice 2]({NEW_GRAPH_3})"
                    print(f"  Updated Choice {i} graph (SIG_2)")
                    updated = True

        if updated:
            try:
                mongo_db.scraped_questions.update_one(
                    {"_id": qid},
                    {"$set": {"question.widgets": widgets}}
                )
                print(f"  Saved changes for {qid}")
                count += 1
            except Exception as e:
                print(f"  Failed to save {qid}: {e}")
                
    print(f"Finished. Updated {count} questions.")

if __name__ == "__main__":
    fix_69324cd9_variants()
