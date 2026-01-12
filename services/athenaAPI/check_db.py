from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
print("Databases:", client.list_database_names())
db = client['athena']
print("Collections in athena:", db.list_collection_names())

# Try to find ANY question to see the ID format
q = db.questions.find_one()
if q:
    print("Sample question ID:", q['_id'], type(q['_id']))

# Try searching by string vs ObjectId if needed (usually handled by pymongo but just in case)
from bson.objectid import ObjectId
try:
    oid = ObjectId('6932cb575853fec4a5597201')
    q2 = db.questions.find_one({'_id': oid})
    if q2:
        print("Found by ObjectId!")
except:
    print("Not a valid ObjectId")
