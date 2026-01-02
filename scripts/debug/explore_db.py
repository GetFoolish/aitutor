from managers.mongodb_manager import mongo_db
import json

def explore():
    client = mongo_db._client
    print(f"Databases: {client.list_database_names()}")
    
    for db_name in ['aitutor', 'ai_tutor']:
        if db_name in client.list_database_names():
            db = client[db_name]
            print(f"\nCollections in {db_name}: {db.list_collection_names()}")
            for coll_name in db.list_collection_names():
                count = db[coll_name].count_documents({})
                print(f"  - {coll_name}: {count} docs")
                # Try finding by ID as both ObjectId and String
                target_id = "691c6e2f41372912898cd98d"
                doc = db[coll_name].find_one({"_id": target_id})
                if doc:
                    print(f"    FOUND {target_id} in {db_name}.{coll_name} (String ID)")
                
                from bson import ObjectId
                try:
                    doc = db[coll_name].find_one({"_id": ObjectId(target_id)})
                    if doc:
                        print(f"    FOUND {target_id} in {db_name}.{coll_name} (ObjectId)")
                except:
                    pass

if __name__ == "__main__":
    explore()
