from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017/')
db = client['aitutor']

print("Dumping ALL questions content to check for placeholders...")

for doc in db.scraped_questions.find():
    sid = str(doc['_id'])
    print(f"\n=== QUESTION {sid} ===")
    
    # Dump widgets
    widgets = {}
    if 'widgets' in doc:
         widgets.update(doc['widgets'])
    if 'perseusItem' in doc:
         p_item = doc['perseusItem']
         if 'question' in p_item and 'widgets' in p_item['question']:
             widgets.update(p_item['question']['widgets'])
         elif 'itemData' in p_item and 'question' in p_item['itemData'] and 'widgets' in p_item['itemData']['question']:
             widgets.update(p_item['itemData']['question']['widgets'])

    for wid, wdata in widgets.items():
         w_type = wdata.get('type', 'unknown')
         w_json = json.dumps(wdata)
         if "ATHENA_HTML_SAFE" in w_json or "ATHENA" in w_json:
              print(f"!!! FOUND PLACEHOLDER IN WIDGET {wid} ({w_type}) !!!")
              print(json.dumps(wdata, indent=2))
         elif w_type in ['table', 'matrix']:
              print(f"Checking {w_type} {wid}...")
              print(json.dumps(wdata, indent=2))

print("\nDone.")
