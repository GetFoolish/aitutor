#!/usr/bin/env python3
"""
Sync data from cloud MongoDB to local MongoDB for testing
This script copies essential collections needed for DASH system testing
"""

from pymongo import MongoClient
import sys

# MongoDB URIs
CLOUD_URI = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"
LOCAL_URI = "mongodb://localhost:27017/"
DB_NAME = "ai_tutor"

# Collections to sync
COLLECTIONS = [
    'generated_skills',
    'scraped_questions',
    'exercises',
    'courses',
    'units',
    'lessons'
]

def sync_collection(cloud_db, local_db, collection_name, batch_size=1000):
    """Sync a single collection from cloud to local"""
    print(f"\n📦 Syncing {collection_name}...")
    
    # Get source collection
    source = cloud_db[collection_name]
    target = local_db[collection_name]
    
    # Count documents
    total_docs = source.count_documents({})
    if total_docs == 0:
        print(f"  ⚠️  No documents found in cloud {collection_name}")
        return
    
    print(f"  Found {total_docs:,} documents in cloud")
    
    # Check if local already has data
    local_count = target.count_documents({})
    if local_count > 0:
        response = input(f"  Local {collection_name} has {local_count:,} documents. Clear and re-sync? (y/n): ")
        if response.lower() == 'y':
            print(f"  Clearing local {collection_name}...")
            target.delete_many({})
        else:
            print(f"  Skipping {collection_name}")
            return
    
    # Sync in batches
    print(f"  Copying documents...")
    cursor = source.find().batch_size(batch_size)
    
    batch = []
    synced = 0
    
    for doc in cursor:
        # Remove _id to avoid duplicate key errors
        if '_id' in doc:
            del doc['_id']
        batch.append(doc)
        
        if len(batch) >= batch_size:
            target.insert_many(batch, ordered=False)
            synced += len(batch)
            print(f"  Progress: {synced:,}/{total_docs:,} ({synced*100//total_docs}%)")
            batch = []
    
    # Insert remaining documents
    if batch:
        target.insert_many(batch, ordered=False)
        synced += len(batch)
    
    print(f"  ✓ Synced {synced:,} documents")

def main():
    print("=" * 60)
    print("Cloud to Local MongoDB Sync Tool")
    print("=" * 60)
    
    try:
        # Connect to cloud MongoDB
        print("\n🌐 Connecting to cloud MongoDB...")
        cloud_client = MongoClient(CLOUD_URI, serverSelectionTimeoutMS=5000)
        cloud_db = cloud_client[DB_NAME]
        cloud_client.admin.command('ping')
        print("  ✓ Connected to cloud")
        
        # Connect to local MongoDB
        print("\n💻 Connecting to local MongoDB...")
        local_client = MongoClient(LOCAL_URI, serverSelectionTimeoutMS=5000)
        local_db = local_client[DB_NAME]
        local_client.admin.command('ping')
        print("  ✓ Connected to local")
        
        # Show what's available
        print("\n📋 Cloud collections:")
        cloud_collections = cloud_db.list_collection_names()
        for col in sorted(cloud_collections):
            count = cloud_db[col].count_documents({})
            if count > 0:
                print(f"  - {col}: {count:,} documents")
        
        # Sync each collection
        print("\n" + "=" * 60)
        print("Starting sync...")
        print("=" * 60)
        
        for collection in COLLECTIONS:
            if collection in cloud_collections:
                sync_collection(cloud_db, local_db, collection)
            else:
                print(f"\n⚠️  Collection '{collection}' not found in cloud")
        
        # Summary
        print("\n" + "=" * 60)
        print("Sync Complete!")
        print("=" * 60)
        print("\n📊 Local MongoDB now has:")
        local_collections = local_db.list_collection_names()
        for col in sorted(local_collections):
            count = local_db[col].count_documents({})
            print(f"  - {col}: {count:,} documents")
        
        # Close connections
        cloud_client.close()
        local_client.close()
        
        print("\n✅ All done! You can now test with local MongoDB.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
