import os
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=60000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Search for the BIOME text to find any related doc, then check for **
SEARCH_TEXT = "Mediterranean forests, woodlands, and scrub biome"

print(f"Searching for all docs related to '{SEARCH_TEXT}' and checking for **...")

for coll_name in db.list_collection_names():
    coll = db[coll_name]
    try:
        # Search by regex in the whole document string representation? No, better query.
        cursor = coll.find({
            "$or": [
                {"question.content": {"$regex": SEARCH_TEXT}},
                {"assessmentData.data.assessmentItem.item.itemData": {"$regex": SEARCH_TEXT}}
            ]
        })
        
        for doc in cursor:
            # Dump to JSON and check for **
            doc_str = json.dumps(doc, default=str)
            count = doc_str.count("**")
            if count > 0:
                print(f"\n[FOUND] Coll: {coll_name}, ID: {doc['_id']}")
                print(f"  Count of **: {count}")
                # Print keys that have it
                for k, v in doc.items():
                    v_str = str(v)
                    if "**" in v_str:
                        print(f"  Found in field '{k}'")
                        if isinstance(v, dict):
                           # Dig deeper
                           for subk, subv in v.items():
                               if "**" in str(subv):
                                   print(f"    -> subfield '{subk}'")
                
                # Check itemData specifically
                try:
                    item_data_str = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
                    if "**" in item_data_str:
                        print("  Found in itemData JSON string")
                        idx = item_data_str.find("**")
                        print(f"  Snippet: {repr(item_data_str[max(0, idx-20):idx+60])}")
                except:
                    pass
    except Exception as e:
         print(f"Error in {coll_name}: {e}")

print("\nScan complete.")
