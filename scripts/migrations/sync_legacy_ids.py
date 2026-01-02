
import sys
import os
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')

# Add project root to path
# Script is in scripts/migrations/, root is 2 levels up
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

# Map: Legacy_ID (Recruiter) -> Real_ID (Database)
ID_MAP = {
  '691c6d6a41372912898cd7ae': '692fac057e334152c5f473e5', # Chart Labels
  '691c6e2f41372912898cd98d': '692f1731f13be434de20c0c6', # Compare (Using formatted text q as base)
  '691c693241372912898ccd8b': '692f1731f13be434de20c0c6', # Bold/Color
  '691c6ace41372912898cd1fb': '692fb45f7e334152c5f474d2', # Font Size / Input Width
  '691c6d7741372912898cd7d5': '692f198f0a3ad6a639ce934d', # Radio 0/1 Bug
  '691c6dde41372912898cd8cc': '692f198f0a3ad6a639ce934d', # Widget Error
}

def sync_ids():
    collection = mongo_db.scraped_questions
    print("SYNCING LEGACY IDs...")

    for legacy_id_str, real_id_str in ID_MAP.items():
        try:
            legacy_oid = ObjectId(legacy_id_str)
            real_oid = ObjectId(real_id_str)

            # 1. Check if legacy already exists
            if collection.find_one({'_id': legacy_oid}):
                print(f"✅ Legacy ID {legacy_id_str} already exists. Skipping.")
                continue

            # 2. Find the real source document
            source_doc = collection.find_one({'_id': real_oid})
            if not source_doc:
                print(f"❌ Source ID {real_id_str} NOT FOUND. Cannot create legacy {legacy_id_str}.")
                continue

            # 3. Prepare clone
            clone_doc = source_doc.copy()
            clone_doc['_id'] = legacy_oid
            
            # Modify questionId to avoid unique index violation
            if 'questionId' in clone_doc:
                clone_doc['questionId'] = f"{clone_doc['questionId']}_legacy_{legacy_id_str}"
            
            # Optional: Add metadata to track origin
            clone_doc['meta_cloned_from'] = real_id_str
            clone_doc['meta_is_legacy_shim'] = True
            
            if 'title' in clone_doc:
                clone_doc['title'] = f"[LEGACY] {clone_doc['title']}"

            # 4. Insert
            collection.insert_one(clone_doc)
            print(f"🚀 CREATED {legacy_id_str} (cloned from {real_id_str})")

        except Exception as e:
            print(f"⚠️ Error processing {legacy_id_str}: {e}")

    print("\nSync Complete.")

if __name__ == "__main__":
    sync_ids()
