"""
MongoDB Database Indexing Script
Phase 4: Database & Data Access

Creates indexes to optimize common query patterns and improve performance.
Run this script after deploying/migrating to ensure indexes are in place.
"""
import sys
import os
from pymongo import ASCENDING, DESCENDING, TEXT

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def create_indexes():
    """Create all necessary indexes for optimal query performance"""
    
    print("Creating MongoDB indexes for performance optimization...")
    
    # Users Collection Indexes
    print("\n1. Creating indexes on 'users' collection...")
    try:
        # Primary lookup by google_id (authentication)
        mongo_db.users.create_index([("google_id", ASCENDING)], unique=True, name="idx_google_id")
        print("   ✓ Created unique index on google_id")
        
        # Lookup by user_id (most common query)
        mongo_db.users.create_index([("user_id", ASCENDING)], unique=True, name="idx_user_id")
        print("   ✓ Created unique index on user_id")
        
        # Email lookup (forgot password, admin queries)
        mongo_db.users.create_index([("google_email", ASCENDING)], name="idx_email")
        print("   ✓ Created index on google_email")
        
        # Grade-based filtering
        mongo_db.users.create_index([("current_grade", ASCENDING)], name="idx_grade")
        print("   ✓ Created index on current_grade")
        
    except Exception as e:
        print(f"   ✗ Error creating users indexes: {e}")
    
    # User Profiles Collection Indexes
    print("\n2. Creating indexes on 'user_profiles' collection...")
    try:
        # Primary lookup
        mongo_db.user_profiles.create_index([("user_id", ASCENDING)], unique=True, name="idx_profile_user_id")
        print("   ✓ Created unique index on user_id")
        
        # Grade filtering for content recommendation
        mongo_db.user_profiles.create_index([("current_grade", ASCENDING)], name="idx_profile_grade")
        print("   ✓ Created index on current_grade")
        
    except Exception as e:
        print(f"   ✗ Error creating user_profiles indexes: {e}")
    
    # Skill States Collection Indexes
    print("\n3. Creating indexes on 'skill_states' collection...")
    try:
        # User skill lookups (most frequent query)
        mongo_db.skill_states.create_index([("user_id", ASCENDING)], name="idx_skill_user_id")
        print("   ✓ Created index on user_id")
        
        # Compound index for user + skill lookups
        mongo_db.skill_states.create_index([("user_id", ASCENDING), ("skillData", ASCENDING)], name="idx_user_skill")
        print("   ✓ Created compound index on user_id + skillData")
        
    except Exception as e:
        print(f"   ✗ Error creating skill_states indexes: {e}")
    
    # Questions Collection Indexes
    print("\n4. Creating indexes on 'questions' collection...")
    try:
        # Question ID lookups
        mongo_db.questions.create_index([("question_id", ASCENDING)], unique=True, name="idx_question_id")
        print("   ✓ Created unique index on question_id")
        
        # Skill-based filtering (for adaptive learning)
        mongo_db.questions.create_index([("skill_ids", ASCENDING)], name="idx_skill_ids")
        print("   ✓ Created index on skill_ids")
        
        # Difficulty filtering
        mongo_db.questions.create_index([("difficulty", ASCENDING)], name="idx_difficulty")
        print("   ✓ Created index on difficulty")
        
        # Compound index for skill + difficulty queries
        mongo_db.questions.create_index(
            [("skill_ids", ASCENDING), ("difficulty", ASCENDING)],
            name="idx_skill_difficulty"
        )
        print("   ✓ Created compound index on skill_ids + difficulty")
        
    except Exception as e:
        print(f"   ✗ Error creating questions indexes: {e}")
    
    # Perseus Questions Collection Indexes
    print("\n5. Creating indexes on 'perseus_questions' collection...")
    try:
        # Primary lookup
        mongo_db.perseus_questions.create_index([("question_id", ASCENDING)], unique=True, name="idx_perseus_id")
        print("   ✓ Created unique index on question_id")
        
        # Skill filtering
        mongo_db.perseus_questions.create_index([("dash_metadata.skill_ids", ASCENDING)], name="idx_perseus_skills")
        print("   ✓ Created index on skill_ids")
        
        # Difficulty + expected time for matching
        mongo_db.perseus_questions.create_index(
            [("dash_metadata.difficulty", ASCENDING), ("dash_metadata.expected_time_seconds", ASCENDING)],
            name="idx_perseus_difficulty_time"
        )
        print("   ✓ Created compound index on difficulty + time")
        
    except Exception as e:
        print(f"   ✗ Error creating perseus_questions indexes: {e}")
    
    # Practice History Collection Indexes
    print("\n6. Creating indexes on 'practice_history' collection (if exists)...")
    try:
        # User history lookups
        if "practice_history" in mongo_db.list_collection_names():
            mongo_db.practice_history.create_index([("user_id", ASCENDING)], name="idx_history_user")
            print("   ✓ Created index on user_id")
            
            # Recent practices (sorted by timestamp)
            mongo_db.practice_history.create_index([("timestamp", DESCENDING)], name="idx_history_time")
            print("   ✓ Created index on timestamp")
            
            # Compound index: user + timestamp for user history queries
            mongo_db.practice_history.create_index(
                [("user_id", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_user_history"
            )
            print("   ✓ Created compound index on user_id + timestamp")
        else:
            print("   ⊘ Collection does not exist yet")
            
    except Exception as e:
        print(f"   ✗ Error creating practice_history indexes: {e}")
    
    # Subject Assessments Collection Indexes (Phase 3)
    print("\n7. Creating indexes on 'subject_assessments' collection...")
    try:
        # Compound unique index for user + subject lookups
        mongo_db.subject_assessments.create_index(
            [("user_id", ASCENDING), ("subject", ASCENDING)],
            unique=True,
            name="idx_user_subject"
        )
        print("   ✓ Created unique compound index on user_id + subject")
        
        # Status filtering for in-progress assessments
        mongo_db.subject_assessments.create_index([("status", ASCENDING)], name="idx_assessment_status")
        print("   ✓ Created index on status")
        
    except Exception as e:
        print(f"   ✗ Error creating subject_assessments indexes: {e}")
    
    print("\n✅ Index creation complete!")
    print("\nTo verify indexes, run:")
    print("  mongo_db.<collection>.index_information()")
    print("\nOr use MongoDB Compass to view indexes visually.")


def drop_all_indexes(confirm=False):
    """Drop all custom indexes (use with CAUTION!)"""
    if not confirm:
        print("⚠️  WARNING: This will drop all custom indexes!")
        print("To confirm, call drop_all_indexes(confirm=True)")
        return
    
    collections = ["users", "user_profiles", "skill_states", "questions", "perseus_questions", "practice_history"]
    
    for coll_name in collections:
        if coll_name in mongo_db.list_collection_names():
            print(f"Dropping indexes from {coll_name}...")
            mongo_db[coll_name].drop_indexes()
            print(f"  ✓ Dropped indexes from {coll_name}")


def analyze_query_performance(collection_name, query):
    """
    Analyze query performance using MongoDB explain()
    
    Usage:
        analyze_query_performance("questions", {"skill_ids": "skill_123", "difficulty": 5})
    """
    print(f"\n📊 Analyzing query on {collection_name}:")
    print(f"Query: {query}\n")
    
    result = mongo_db[collection_name].find(query).explain()
    
    execution_stats = result.get("executionStats", {})
    print(f"Execution Time: {execution_stats.get('executionTimeMillis', 'N/A')} ms")
    print(f"Documents Examined: {execution_stats.get('totalDocsExamined', 'N/A')}")
    print(f"Documents Returned: {execution_stats.get('nReturned', 'N/A')}")
    print(f"Index Used: {result.get('queryPlanner', {}).get('winningPlan', {}).get('inputStage', {}).get('indexName', 'Collection Scan (No Index)')}")
    
    efficiency = execution_stats.get("nReturned", 0) / max(execution_stats.get("totalDocsExamined", 1), 1)
    print(f"Efficiency: {efficiency:.2%} (higher is better)")
    
    if efficiency < 0.5:
        print("⚠️  Low efficiency - consider adding an index!")
    else:
        print("✓ Good efficiency")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB Index Management")
    parser.add_argument("--create", action="store_true", help="Create all indexes")
    parser.add_argument("--drop", action="store_true", help="Drop all custom indexes")
    parser.add_argument("--analyze", nargs=2, metavar=('COLLECTION', 'QUERY'), help="Analyze query performance")
    
    args = parser.parse_args()
    
    if args.create:
        create_indexes()
    elif args.drop:
        drop_all_indexes(confirm=True)
    elif args.analyze:
        import json
        query = json.loads(args.analyze[1])
        analyze_query_performance(args.analyze[0], query)
    else:
        # Default: create indexes
        create_indexes()
