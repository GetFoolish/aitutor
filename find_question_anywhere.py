from managers.mongodb_manager import mongo_db
import json

def list_all():
    client = mongo_db._client
    dbs = client.list_database_names()
    print(f"Databases: {dbs}")
    
    for db_name in dbs:
        db = client[db_name]
        colls = db.list_collection_names()
        print(f"Database: {db_name}, Collections: {colls}")
        for coll_name in colls:
            count = db[coll_name].count_documents({})
            print(f"  - {coll_name}: {count} docs")
            if count > 0:
                # Try to find the question by ID in any collection
                q = db[coll_name].find_one({"_id": "691c6be841372912898cd488"})
                if not q:
                    from bson import ObjectId
                    try:
                        q = db[coll_name].find_one({"_id": ObjectId("691c6be841372912898cd488")})
                    except:
                        pass
                if q:
                    print(f"FOUND QUESTION IN {db_name}.{coll_name}")
                    q['_id'] = str(q['_id'])
                    print(json.dumps(q, indent=2))

if __name__ == "__main__":
    list_all()
