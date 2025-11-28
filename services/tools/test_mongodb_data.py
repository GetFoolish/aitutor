"""
Test Script: Verify MongoDB Data After Migration
Checks that all data was migrated correctly
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

def test_mongodb_data():
    """Test that all data is accessible in MongoDB"""
    
    print("\n" + "="*80)
    print("TESTING MONGODB DATA")
    print("="*80 + "\n")
    
    # Connect to MongoDB using environment variables
    uri = os.getenv('MONGODB_URI')
    if not uri:
        print("❌ ERROR: MONGODB_URI not found in environment variables")
        print("   Please create a .env file with MONGODB_URI")
        print("   See .env.example for template")
        return False
    
    db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
    client = MongoClient(uri)
    db = client[db_name]
    
    print(f"✅ Connected to MongoDB (database: {db_name})\n")
    
    all_tests_passed = True
    
    # Test 1: Skills Collection
    print("🔍 Test 1: Skills Collection")
    print("-" * 40)
    skills = db.skills
    skill_count = skills.count_documents({})
    print(f"   Total skills: {skill_count}")
    
    if skill_count == 0:
        print("   ❌ FAIL: No skills found in MongoDB")
        all_tests_passed = False
    else:
        # Test: Can we find a kindergarten skill?
        k_skill = skills.find_one({"grade_level": "K"})
        if k_skill:
            print(f"   ✅ Sample K skill: {k_skill['name']}")
        else:
            print("   ❌ FAIL: No kindergarten skills found")
            all_tests_passed = False
        
        # Test: Can we find a skill with prerequisites?
        skill_with_prereq = skills.find_one({"prerequisites": {"$ne": []}})
        if skill_with_prereq:
            print(f"   ✅ Sample skill with prereqs: {skill_with_prereq['name']} → {skill_with_prereq['prerequisites']}")
        else:
            print("   ⚠️  Warning: No skills with prerequisites found")
    
    print()
    
    # Test 2: DASH Questions Collection
    print("🔍 Test 2: DASH Questions Collection")
    print("-" * 40)
    questions = db.dash_questions
    question_count = questions.count_documents({})
    print(f"   Total DASH questions: {question_count}")
    
    if question_count == 0:
        print("   ❌ FAIL: No DASH questions found in MongoDB")
        all_tests_passed = False
    else:
        # Test: Questions per grade
        for grade in ['K', 'GRADE_1', 'GRADE_2', 'GRADE_3']:
            count = questions.count_documents({"grade": grade})
            print(f"   • {grade}: {count} questions")
        
        # Test: Can we find a question for a specific skill?
        sample_q = questions.find_one({"skill_id": "counting_1_10"})
        if sample_q:
            print(f"   ✅ Sample question: {sample_q['content'][:50]}...")
        else:
            print("   ⚠️  Warning: No questions for 'counting_1_10' skill")
    
    print()
    
    # Test 3: Perseus Questions Collection
    print("🔍 Test 3: Perseus Questions Collection")
    print("-" * 40)
    perseus = db.perseus_questions
    perseus_count = perseus.count_documents({})
    print(f"   Total Perseus questions: {perseus_count}")
    
    if perseus_count == 0:
        print("   ❌ FAIL: No Perseus questions found in MongoDB")
        all_tests_passed = False
    else:
        # Test: Can we find questions by skill prefix?
        for prefix in ['1.1.1.1', '1.1.1.2', '1.1.2.1']:
            count = perseus.count_documents({"skill_prefix": prefix})
            print(f"   • Skill prefix {prefix}: {count} questions")
        
        # Test: Check a sample Perseus question structure
        sample_perseus = perseus.find_one({"skill_prefix": "1.1.1.1"})
        if sample_perseus:
            has_question = 'question' in sample_perseus
            has_hints = 'hints' in sample_perseus and len(sample_perseus['hints']) > 0
            has_answer_area = 'answerArea' in sample_perseus
            
            print(f"   ✅ Sample Perseus structure:")
            print(f"      - Has question: {has_question}")
            print(f"      - Has hints: {has_hints}")
            print(f"      - Has answerArea: {has_answer_area}")
            
            if not (has_question and has_hints and has_answer_area):
                print("   ⚠️  Warning: Perseus question missing some fields")
        else:
            print("   ❌ FAIL: Cannot find sample Perseus question")
            all_tests_passed = False
    
    print()
    
    # Test 4: Indexes
    print("🔍 Test 4: Indexes")
    print("-" * 40)
    
    skills_indexes = list(skills.list_indexes())
    questions_indexes = list(questions.list_indexes())
    perseus_indexes = list(perseus.list_indexes())
    
    print(f"   Skills indexes: {len(skills_indexes)} ({', '.join([idx['name'] for idx in skills_indexes])})")
    print(f"   DASH Questions indexes: {len(questions_indexes)} ({', '.join([idx['name'] for idx in questions_indexes])})")
    print(f"   Perseus indexes: {len(perseus_indexes)} ({', '.join([idx['name'] for idx in perseus_indexes])})")
    
    print()
    
    # Test 5: Query Performance Test
    print("🔍 Test 5: Query Performance")
    print("-" * 40)
    
    import time
    
    # Test skill lookup
    start = time.time()
    result = skills.find_one({"skill_id": "counting_1_10"})
    duration = time.time() - start
    print(f"   Skill lookup by ID: {duration*1000:.2f}ms {'✅' if result else '❌'}")
    
    # Test question lookup by skill
    start = time.time()
    result = list(questions.find({"skill_id": "counting_1_10"}).limit(10))
    duration = time.time() - start
    print(f"   Questions by skill_id: {duration*1000:.2f}ms (found {len(result)}) {'✅' if result else '❌'}")
    
    # Test Perseus lookup by prefix
    start = time.time()
    result = list(perseus.find({"skill_prefix": "1.1.1.1"}).limit(10))
    duration = time.time() - start
    print(f"   Perseus by prefix: {duration*1000:.2f}ms (found {len(result)}) {'✅' if result else '❌'}")
    
    print()
    
    # Final Summary
    print("="*80)
    if all_tests_passed:
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nMongoDB data is ready. You can now:")
        print("  1. Update code to use MongoDB")
        print("  2. Test the system with real data")
        print("  3. Keep local files as backup")
    else:
        print("❌ SOME TESTS FAILED!")
        print("="*80)
        print("\nPlease check the errors above and:")
        print("  1. Verify migration scripts ran successfully")
        print("  2. Check MongoDB connection")
        print("  3. Re-run migrations if needed")
    print("="*80 + "\n")
    
    client.close()
    return all_tests_passed

if __name__ == "__main__":
    try:
        success = test_mongodb_data()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

