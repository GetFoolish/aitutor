"""
Migration Script 3: Load Perseus Questions into MongoDB
Phase 1 of MongoDB migration
This migrates 4,835 Perseus question files
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from dotenv import load_dotenv
import json
import glob
from datetime import datetime

# Load environment variables
load_dotenv()

def migrate_perseus_questions():
    """Load Perseus questions from CurriculumBuilder/*.json into MongoDB"""
    
    print("="*80)
    print("MIGRATION SCRIPT 3: Perseus Questions → MongoDB")
    print("="*80)
    
    # Connect to MongoDB using environment variables
    uri = os.getenv('MONGODB_URI')
    if not uri:
        print("\n❌ ERROR: MONGODB_URI not found in environment variables")
        print("   Please create a .env file with MONGODB_URI")
        print("   See .env.example for template")
        return False
    
    db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
    client = MongoClient(uri)
    db = client[db_name]
    perseus_collection = db['perseus_questions']
    
    print(f"\n✅ Connected to MongoDB (database: {db_name})")
    
    # Create indexes
    print("\n📊 Creating indexes...")
    perseus_collection.create_index("slug", unique=True)
    perseus_collection.create_index("skill_prefix")
    perseus_collection.create_index("filename")
    print("   ✅ Indexes created: slug (unique), skill_prefix, filename")
    
    # Find all Perseus files (use absolute path from project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    perseus_dir = os.path.join(project_root, "SherlockEDApi", "CurriculumBuilder")
    pattern = os.path.join(perseus_dir, "*.json")
    perseus_files = glob.glob(pattern)
    
    print(f"\n📂 Found {len(perseus_files)} Perseus question files")
    
    if len(perseus_files) == 0:
        print(f"   ❌ No files found in {perseus_dir}")
        print(f"   Current directory: {os.getcwd()}")
        return False
    
    # Migrate questions
    print("\n🔄 Migrating Perseus questions to MongoDB...")
    print(f"   (This may take a few minutes...)\n")
    
    migrated = 0
    updated = 0
    errors = 0
    
    for i, file_path in enumerate(perseus_files, 1):
        try:
            # Read Perseus file
            with open(file_path, 'r', encoding='utf-8') as f:
                perseus_data = json.load(f)
            
            # Extract metadata from filename
            filename = os.path.basename(file_path)
            # Example: "1.1.1.1.5_x8666caea68265b0f.json" → slug = "1.1.1.1.5"
            slug = filename.split('_')[0] if '_' in filename else filename.replace('.json', '')
            
            # Extract skill prefix (first 4 parts)
            # "1.1.1.1.5" → "1.1.1.1"
            parts = slug.split('.')
            skill_prefix = '.'.join(parts[:4]) if len(parts) >= 4 else slug
            
            # Create document
            document = {
                "slug": slug,
                "filename": filename,
                "skill_prefix": skill_prefix,
                "question": perseus_data.get("question", {}),
                "answerArea": perseus_data.get("answerArea", {}),
                "hints": perseus_data.get("hints", []),
                "itemDataVersion": perseus_data.get("itemDataVersion", {}),
                "uploaded_at": datetime.utcnow()
            }
            
            # Upsert (insert or update)
            result = perseus_collection.update_one(
                {"slug": slug},
                {"$set": document},
                upsert=True
            )
            
            if result.upserted_id:
                migrated += 1
            else:
                updated += 1
            
            # Progress indicator every 500 files
            if i % 500 == 0:
                print(f"   Progress: {i}/{len(perseus_files)} files processed...")
        
        except Exception as e:
            errors += 1
            if errors <= 5:  # Only show first 5 errors
                print(f"   ❌ Error processing {filename}: {e}")
    
    # Verify
    total_in_db = perseus_collection.count_documents({})
    
    print(f"\n{'='*80}")
    print("MIGRATION COMPLETE!")
    print(f"{'='*80}")
    print(f"   ✅ New questions inserted: {migrated}")
    print(f"   🔄 Existing questions updated: {updated}")
    print(f"   ❌ Errors: {errors}")
    print(f"   📁 Total Perseus questions in MongoDB: {total_in_db}")
    print(f"{'='*80}\n")
    
    # Show skill prefix distribution
    print("📊 Perseus questions by skill prefix (top 10):")
    pipeline = [
        {"$group": {"_id": "$skill_prefix", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    for result in perseus_collection.aggregate(pipeline):
        print(f"   • {result['_id']}: {result['count']} questions")
    
    print()
    
    # Show sample
    sample = perseus_collection.find_one({"skill_prefix": "1.1.1.1"})
    if sample:
        print("📋 Sample Perseus question in MongoDB:")
        print(f"   Slug: {sample['slug']}")
        print(f"   Skill Prefix: {sample['skill_prefix']}")
        print(f"   Filename: {sample['filename']}")
        print(f"   Has question: {'question' in sample}")
        print(f"   Has hints: {len(sample.get('hints', []))} hints")
        print()
    
    client.close()
    return True

if __name__ == "__main__":
    try:
        migrate_perseus_questions()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

