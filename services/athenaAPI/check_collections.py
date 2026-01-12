from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['aitutor']
print("Collections in aitutor:", db.list_collection_names())

# Check first collection for any document
for coll_name in db.list_collection_names():
    print(f"\n--- Collection: {coll_name} ---")
    doc = db[coll_name].find_one()
    if doc:
        print("Sample ID:", doc.get('_id'), type(doc.get('_id')))
        if 'title' in doc:
             print("Title:", doc['title'])
