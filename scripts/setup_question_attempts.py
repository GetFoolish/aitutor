"""
Setup script for question_attempts collection.
This creates the new collection structure for future-proof student performance tracking.
"""
from managers.mongodb_manager import mongo_db
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def setup_question_attempts():
    """Create question_attempts collection with proper indexes"""
    
    print("🔧 Setting up question_attempts collection...")
    
    # Create indexes for fast querying
    mongo_db.question_attempts.create_index([("user_id", 1), ("timestamp", -1)])
    mongo_db.question_attempts.create_index("question_id")
    mongo_db.question_attempts.create_index("timestamp")
    
    print("✅ Created question_attempts collection with indexes:")
    print("  - user_id + timestamp (for fetching user history)")
    print("  - question_id (for looking up question → skill mapping)")
    print("  - timestamp (for chronological queries)")
    
    # Check if we have existing performance data to migrate
    try:
        existing_count = mongo_db.student_performance.count_documents({})
        print(f"\n📊 Found {existing_count} existing student_performance records")
        
        if existing_count > 0:
            print("ℹ️  Note: Old student_performance collection will remain for backward compatibility")
            print("   New question submissions will use question_attempts going forward")
    except Exception as e:
        print(f"ℹ️  No existing student_performance collection found (this is normal for new setups)")
    
    # Verify the setup
    indexes = list(mongo_db.question_attempts.list_indexes())
    print(f"\n✅ Verified {len(indexes)} indexes created successfully")
    
    print("\n🎉 Setup complete! The system is ready to track question attempts.")
    print("\nNext steps:")
    print("  1. Restart DASH API to use new endpoints")
    print("  2. Student progress will now be future-proof!")

if __name__ == "__main__":
    setup_question_attempts()
