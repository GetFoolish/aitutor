from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017/')
db = client['aitutor']

target = '6932cb575853fec4a5597201'
print(f"Searching for ID: {target}")

found_target = False
first_table_dumped = False
all_ids = []

# Linear scan of scraped_questions
for doc in db.scraped_questions.find():
    sid = str(doc['_id'])
    all_ids.append(sid)
    
    is_target = (sid == target)
    
    # Check for widgets
    widgets = {}
    if 'widgets' in doc:
         widgets.update(doc['widgets'])
    if 'perseusItem' in doc:
         p_item = doc['perseusItem']
         if 'question' in p_item and 'widgets' in p_item['question']:
             widgets.update(p_item['question']['widgets'])
         elif 'itemData' in p_item and 'question' in p_item['itemData'] and 'widgets' in p_item['itemData']['question']:
             widgets.update(p_item['itemData']['question']['widgets'])

    has_table = False
    for wid, wdata in widgets.items():
         w_type = wdata.get('type', 'unknown')
         if w_type in ['table', 'matrix']:
              has_table = True
              # Dump if it's the target OR if it's the first table we see (as reference)
              if is_target or not first_table_dumped:
                   print(f"\n--- FOUND {w_type.upper()} WIDGET IN {sid} ---")
                   print(f"Widget ID: {wid}")
                   print(json.dumps(wdata, indent=2))
                   first_table_dumped = True

    if is_target:
        found_target = True
        print(f"\n!!! FOUND TARGET ID: {sid} !!!")
        print("Title:", doc.get('title'))
        # If we didn't dump table above (e.g. no table found in target), dump whole doc structure
        if not has_table:
             print("No table/matrix widget found in target widgets list.")
             print("Keys:", doc.keys())
             if 'content' in doc:
                  print("Content:", doc['content'])

# Save all IDs to file for inspection
with open('all_ids_dump.txt', 'w') as f:
    for i in sorted(all_ids):
        f.write(f"{i}\n")

if not found_target:
    print("\nID NOT FOUND in scan.")
    print(f"Total documents scanned: {len(all_ids)}")
