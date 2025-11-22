"""
Create a test user in MongoDB users collection for Phase 2 testing.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
import time

def create_test_user():
    """Create a test user in MongoDB"""
    
    # ============================================================
    # 🎯 CHANGE THESE VALUES TO TEST DIFFERENT GRADES:
    # ============================================================
    user_id = "mongodb_test_user"
    age = 6  # Change age here (5=K, 6=Grade1, 7=Grade2, 8=Grade3, etc.)
    current_grade = "GRADE_1"  # Must match age (5→K, 6→GRADE_1, 7→GRADE_2, etc.)
    # ============================================================
    
    # Note: MongoDB has Perseus questions for K-2 only
    # For best results, test with age 5-7 (K, Grade 1, Grade 2)
    
    test_user = {
        "user_id": user_id,
        "age": age,
        "current_grade": current_grade,
        "created_at": time.time(),
        "last_updated": time.time(),
        "skill_states": {
            # Cold-start initialized skills (will be auto-populated based on grade)
            # These are just starter skills - DASH will initialize all skills on first use
            "counting_1_10": {
                "memory_strength": 2.0 if age >= 5 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "number_recognition": {
                "memory_strength": 2.0 if age >= 5 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "basic_shapes": {
                "memory_strength": 2.0 if age >= 5 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "addition_basic": {
                "memory_strength": 2.0 if age >= 6 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "subtraction_basic": {
                "memory_strength": 2.0 if age >= 6 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "counting_100": {
                "memory_strength": 2.0 if age >= 6 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "addition_2digit": {
                "memory_strength": 2.0 if age >= 7 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "subtraction_2digit": {
                "memory_strength": 2.0 if age >= 7 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            },
            "multiplication_intro": {
                "memory_strength": 2.0 if age >= 7 else 0.0,
                "last_practice_time": None,
                "practice_count": 0,
                "correct_count": 0
            }
        },
        "question_history": [],
        "student_notes": {}
    }
    
    # Check if user already exists
    existing = mongo_db.users.find_one({"user_id": user_id})
    if existing:
        print(f"⚠️  User '{user_id}' already exists in MongoDB")
        print("   Deleting old version and creating fresh...")
        mongo_db.users.delete_one({"user_id": user_id})
    
    # Insert the test user
    result = mongo_db.users.insert_one(test_user)
    
    print("\n" + "="*60)
    print("✅ Test User Created in MongoDB!")
    print("="*60)
    print(f"  User ID: {user_id}")
    print(f"  Age: {age} years old")
    print(f"  Grade: {current_grade}")
    print(f"  Skills Initialized: {len(test_user['skill_states'])}")
    print(f"  MongoDB _id: {result.inserted_id}")
    print("="*60)
    
    # Show Perseus availability
    if age <= 7:
        print("\n✅ Good choice! Perseus questions available for this grade.")
    else:
        print(f"\n⚠️  Note: MongoDB has limited Perseus questions for Grade {age-5}+")
        print("   System will use Grade 2 questions as best available.")
    
    # Verify it was created
    retrieved = mongo_db.users.find_one({"user_id": user_id})
    if retrieved:
        print("\n✅ Verification: User successfully retrieved from MongoDB")
        print(f"   Age: {retrieved['age']}")
        print(f"   Grade: {retrieved['current_grade']}")
        print(f"   Skills: {len(retrieved['skill_states'])}")
    else:
        print("\n❌ Error: Could not retrieve user after creation!")
    
    print("\n📝 Next Steps:")
    print("   1. Restart backend: python services/DashSystem/dash_api.py")
    print(f"   2. Test API with: user_id={user_id}")
    print(f"   3. Age ({age}) will be fetched from MongoDB, not frontend!")
    print("\n💡 Tip: To test different ages, edit lines 18-20 in this script")

if __name__ == "__main__":
    try:
        create_test_user()
    except Exception as e:
        print(f"\n❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()

