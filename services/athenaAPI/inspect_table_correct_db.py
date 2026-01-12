from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017/')
db = client['aitutor']  # CORRECT DATABASE NAME
q = db.questions.find_one({'_id': '6932cb575853fec4a5597201'})

if q:
    print("\n=== QUESTION DATA FOUND ===")
    if 'content' in q:
        print("Content sample:", repr(q['content'])[:500])
    
    found_table = False
    
    # Check top-level widgets
    if 'widgets' in q:
        print("\nWidgets found:", list(q['widgets'].keys()))
        for wid, wdata in q['widgets'].items():
            if wdata['type'] == 'table' or 'table' in wid:
                print(f"\n--- Widget {wid} ({wdata['type']}) ---")
                print(json.dumps(wdata, indent=2))
                found_table = True
    
    # Check Perseus item structure
    if 'perseusItem' in q:
         print("\nPerseus Item Widgets found:")
         try:
             widgets = q['perseusItem']['question']['widgets']
             for wid, wdata in widgets.items():
                if wdata['type'] == 'table' or 'table' in wid:
                    print(f"\n--- Widget {wid} ({wdata['type']}) ---")
                    print(json.dumps(wdata, indent=2))
                    found_table = True
         except KeyError:
             pass
             
    if not found_table:
        print("\nNO TABLE WIDGET FOUND. Content likely uses Markdown table.")
        if 'content' in q:
            print("\nContent full dump for Markdown check:")
            print(q['content'])
            
else:
    print("Question not found in 'aitutor' database")
