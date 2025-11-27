"""
Migration Script 2: Load DASH Questions into MongoDB
Phase 1 of MongoDB migration
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from pymongo import MongoClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def migrate_dash_questions():
    """Load DASH questions from curriculum.json into MongoDB"""
    
    print("="*80)
    print("MIGRATION SCRIPT 2: DASH Questions → MongoDB")
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
    questions_collection = db['dash_questions']
    
    print(f"\n✅ Connected to MongoDB (database: {db_name})")
    
    # Create indexes
    print("\n📊 Creating indexes...")
    questions_collection.create_index("question_id", unique=True)
    questions_collection.create_index("skill_id")
    questions_collection.create_index("grade")
    questions_collection.create_index("difficulty")
    print("   ✅ Indexes created: question_id (unique), skill_id, grade, difficulty")
    
    # Load curriculum.json (use absolute path from project root)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    curriculum_file = os.path.join(project_root, "services", "QuestionBankGenerator", "QuestionsBank", "curriculum.json")
    print(f"\n📂 Reading {curriculum_file}...")
    
    with open(curriculum_file, 'r', encoding='utf-8') as f:
        curriculum = json.load(f)
    
    print(f"   ✅ Loaded curriculum with {len(curriculum['grades'])} grades")
    
    # Migrate questions
    print("\n🔄 Migrating DASH questions to MongoDB...")
    migrated = 0
    updated = 0
    total_questions = 0
    
    for grade_key, grade_data in curriculum['grades'].items():
        grade_name = grade_data['grade_name']
        print(f"\n   Processing {grade_name} ({grade_key})...")
        
        for skill_data in grade_data['skills']:
            skill_id = skill_data['skill_id']
            questions = skill_data['questions']
            
            for question in questions:
                total_questions += 1
                
                document = {
                    "question_id": question['question_id'],
                    "skill_id": skill_id,
                    "grade": grade_key,
                    "grade_name": grade_name,
                    "content": question['content'],
                    "difficulty": question['difficulty'],
                    "expected_time_seconds": question.get('expected_time_seconds', 60),
                    "correct_answer": question.get('correct_answer', ''),
                    "metadata": question.get('metadata', {}),
                    "order": skill_data.get('order', 0),
                    "mastery_threshold": skill_data.get('mastery_threshold', 0.8)
                }
                
                # Upsert (insert or update)
                result = questions_collection.update_one(
                    {"question_id": document['question_id']},
                    {"$set": document},
                    upsert=True
                )
                
                if result.upserted_id:
                    migrated += 1
                else:
                    updated += 1
            
            print(f"      • {skill_id}: {len(questions)} questions")
    
    # Verify
    total_in_db = questions_collection.count_documents({})
    
    print(f"\n{'='*80}")
    print("MIGRATION COMPLETE!")
    print(f"{'='*80}")
    print(f"   ✅ New questions inserted: {migrated}")
    print(f"   🔄 Existing questions updated: {updated}")
    print(f"   📁 Total questions in MongoDB: {total_in_db}")
    print(f"   📊 Questions by grade:")
    
    # Show breakdown by grade
    for grade in ['K', 'GRADE_1', 'GRADE_2', 'GRADE_3', 'GRADE_4', 'GRADE_5', 
                  'GRADE_6', 'GRADE_7', 'GRADE_8', 'GRADE_9', 'GRADE_10', 
                  'GRADE_11', 'GRADE_12']:
        count = questions_collection.count_documents({"grade": grade})
        if count > 0:
            print(f"      • {grade}: {count} questions")
    
    print(f"{'='*80}\n")
    
    # Show sample
    sample = questions_collection.find_one({"grade": "K"})
    if sample:
        print("📋 Sample DASH question in MongoDB:")
        print(f"   ID: {sample['question_id']}")
        print(f"   Skill: {sample['skill_id']}")
        print(f"   Grade: {sample['grade']}")
        print(f"   Content: {sample['content']}")
        print(f"   Difficulty: {sample['difficulty']}")
        print()
    
    client.close()
    return True

if __name__ == "__main__":
    try:
        migrate_dash_questions()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

