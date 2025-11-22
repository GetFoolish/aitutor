"""
Migration Script 1: Load Skills into MongoDB
Phase 1 of MongoDB migration
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def migrate_skills():
    """Load skills from skills.json into MongoDB"""
    
    print("="*80)
    print("MIGRATION SCRIPT 1: Skills → MongoDB")
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
    skills_collection = db['skills']
    
    print(f"\n✅ Connected to MongoDB (database: {db_name})")
    
    # Create indexes
    print("\n📊 Creating indexes...")
    skills_collection.create_index("skill_id", unique=True)
    skills_collection.create_index("grade_level")
    skills_collection.create_index("prerequisites")
    print("   ✅ Indexes created: skill_id (unique), grade_level, prerequisites")
    
    # Load skills.json (use absolute path from project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skills_file = os.path.join(project_root, "QuestionsBank", "skills.json")
    print(f"\n📂 Reading {skills_file}...")
    
    with open(skills_file, 'r', encoding='utf-8') as f:
        skills_data = json.load(f)
    
    print(f"   ✅ Loaded {len(skills_data)} skills from file")
    
    # Migrate each skill
    print("\n🔄 Migrating skills to MongoDB...")
    migrated = 0
    updated = 0
    
    for skill_id, skill_info in skills_data.items():
        document = {
            "skill_id": skill_id,
            "name": skill_info['name'],
            "grade_level": skill_info['grade_level'],
            "prerequisites": skill_info['prerequisites'],
            "forgetting_rate": skill_info['forgetting_rate'],
            "difficulty": skill_info['difficulty'],
            "description": skill_info.get('description', ''),
            "order": skill_info.get('order', 0)
        }
        
        # Upsert (insert or update)
        result = skills_collection.update_one(
            {"skill_id": skill_id},
            {"$set": document},
            upsert=True
        )
        
        if result.upserted_id:
            migrated += 1
        else:
            updated += 1
    
    # Verify
    total_in_db = skills_collection.count_documents({})
    
    print(f"\n{'='*80}")
    print("MIGRATION COMPLETE!")
    print(f"{'='*80}")
    print(f"   ✅ New skills inserted: {migrated}")
    print(f"   🔄 Existing skills updated: {updated}")
    print(f"   📁 Total skills in MongoDB: {total_in_db}")
    print(f"{'='*80}\n")
    
    # Show sample
    sample = skills_collection.find_one({"skill_id": "counting_1_10"})
    if sample:
        print("📋 Sample skill in MongoDB:")
        print(f"   ID: {sample['skill_id']}")
        print(f"   Name: {sample['name']}")
        print(f"   Grade: {sample['grade_level']}")
        print(f"   Prerequisites: {sample['prerequisites']}")
        print()
    
    client.close()
    return True

if __name__ == "__main__":
    try:
        migrate_skills()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

