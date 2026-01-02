
from managers.mongodb_manager import mongo_db
from bson import ObjectId

id_str = '691c6d6a41372912898cd7ae'
print(f"Checking ID: {id_str}")

# Try finding by ObjectId
doc_oid = mongo_db.scraped_questions.find_one({'_id': ObjectId(id_str)})
if doc_oid:
    print(f"✅ Found by ObjectId! Title: {doc_oid.get('title')}")
else:
    print("❌ NOT found by ObjectId.")

# Try finding by String
doc_str = mongo_db.scraped_questions.find_one({'_id': id_str})
if doc_str:
    print(f"✅ Found by String! Title: {doc_str.get('title')}")
else:
    print("❌ NOT found by String.")

# List all collections to be sure
print(f"Collections: {mongo_db.db.list_collection_names()}")
