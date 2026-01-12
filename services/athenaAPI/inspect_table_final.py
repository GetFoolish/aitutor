from pymongo import MongoClient
from bson.objectid import ObjectId
import json

client = MongoClient('mongodb://localhost:27017/')
db = client['aitutor']
try:
    oid = ObjectId('69334af918bcab85650eed24')
    q = db.scraped_questions.find_one({'_id': oid})
except Exception as e:
    print(f"Invalid ObjectId: {e}")
    q = None

if q:
    print("\n=== QUESTION DATA FOUND ===")
    
    found = False
    # Check widgets in potential locations
    widgets = {}
    if 'widgets' in q:
        widgets.update(q['widgets'])
    if 'perseusItem' in q and 'question' in q['perseusItem'] and 'widgets' in q['perseusItem']['question']:
        widgets.update(q['perseusItem']['question']['widgets'])
        
    print("\nWidgets found:", list(widgets.keys()))
    
    for wid, wdata in widgets.items():
        if True: # Print ALL widgets
            print(f"\n--- Widget {wid} ({wdata['type']}) ---")
            print(json.dumps(wdata, indent=2))
            found = True
            
    if not found:
        print("\nNO TABLE WIDGET FOUND.")
        if 'content' in q:
             print("Content:", q['content'])
             
else:
    print("Question not found in 'scraped_questions'")
