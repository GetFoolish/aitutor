from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017/')
db = client['athena']
q = db.questions.find_one({'_id': '6932cb575853fec4a5597201'})

if q:
    print("\n=== QUESTION DATA ===")
    # Print relevant parts to identify table structure
    if 'content' in q:
        print("Content sample:", repr(q['content'])[:500])
    
    if 'widgets' in q:
        print("\nWidgets found:", list(q['widgets'].keys()))
        for wid, wdata in q['widgets'].items():
            if wdata['type'] == 'table' or 'table' in wid:
                print(f"\n--- Widget {wid} ({wdata['type']}) ---")
                print(json.dumps(wdata, indent=2))
    elif 'perseusItem' in q:
         print("\nPerseus Item Widgets found:")
         widgets = q['perseusItem']['question']['widgets']
         for wid, wdata in widgets.items():
            if wdata['type'] == 'table' or 'table' in wid:
                print(f"\n--- Widget {wid} ({wdata['type']}) ---")
                print(json.dumps(wdata, indent=2))

else:
    print("Question not found")
