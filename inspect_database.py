"""
MongoDB Database Inspector
Inspects ai_tutor and questions_db databases to show what data and questions each contains.
"""

import os
import sys
from pymongo import MongoClient
from pprint import pprint
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def inspect_database(client, db_name):
    """Inspect a specific database and show all collections and their data"""
    print(f"\n{'='*80}")
    print(f"DATABASE: {db_name}")
    print(f"{'='*80}\n")
    
    try:
        db = client[db_name]
        
        # List all collections
        collections = db.list_collection_names()
        
        if not collections:
            print(f"  ⚠️  No collections found in {db_name}")
            return
        
        print(f"📚 Collections found: {len(collections)}")
        print(f"   {', '.join(collections)}\n")
        
        # Inspect each collection
        for collection_name in sorted(collections):
            collection = db[collection_name]
            count = collection.count_documents({})
            
            print(f"{'─'*80}")
            print(f"📦 Collection: {collection_name}")
            print(f"   Documents: {count:,}")
            
            if count == 0:
                print(f"   ⚠️  Empty collection")
                continue
            
            # Get sample document to show structure
            sample = collection.find_one()
            if sample:
                print(f"\n   📄 Sample Document Structure:")
                print(f"   Fields: {', '.join(sorted(sample.keys()))}")
                
                # Show sample data (truncated)
                print(f"\n   Sample Document (first 500 chars):")
                sample_str = str(sample)
                if len(sample_str) > 500:
                    print(f"   {sample_str[:500]}...")
                else:
                    print(f"   {sample_str}")
            
            # Special handling for questions collection
            if collection_name == 'questions':
                inspect_questions_collection(collection, db_name)
            
            # Special handling for scraped_questions collection
            elif collection_name == 'scraped_questions':
                inspect_scraped_questions_collection(collection)
            
            print()
    
    except Exception as e:
        print(f"  ❌ Error inspecting {db_name}: {e}")


def inspect_questions_collection(collection, db_name):
    """Inspect questions collection with detailed analysis"""
    print(f"\n   🔍 Questions Collection Analysis:")
    
    # Count by field presence
    total = collection.count_documents({})
    
    # Check for different field naming conventions
    has_question_id = collection.count_documents({"question_id": {"$exists": True}})
    has_questionId = collection.count_documents({"questionId": {"$exists": True}})
    has_perseus_json = collection.count_documents({"perseus_json": {"$exists": True}})
    has_assessmentData = collection.count_documents({"assessmentData": {"$exists": True}})
    has_exercise_id = collection.count_documents({"exercise_id": {"$exists": True}})
    has_exerciseId = collection.count_documents({"exerciseId": {"$exists": True}})
    has_sha = collection.count_documents({"sha": {"$exists": True}})
    
    print(f"      Total questions: {total:,}")
    print(f"      Field Analysis:")
    print(f"        - question_id (snake_case): {has_question_id:,}")
    print(f"        - questionId (camelCase): {has_questionId:,}")
    print(f"        - perseus_json: {has_perseus_json:,}")
    print(f"        - assessmentData: {has_assessmentData:,}")
    print(f"        - exercise_id (snake_case): {has_exercise_id:,}")
    print(f"        - exerciseId (camelCase): {has_exerciseId:,}")
    print(f"        - sha (for deduplication): {has_sha:,}")
    
    # Get sample question to show structure
    sample = collection.find_one()
    if sample:
        print(f"\n      Sample Question Fields:")
        for key in sorted(sample.keys()):
            value = sample[key]
            if isinstance(value, dict):
                print(f"        - {key}: {{dict with {len(value)} keys}}")
            elif isinstance(value, list):
                print(f"        - {key}: [list with {len(value)} items]")
            elif isinstance(value, str) and len(value) > 50:
                print(f"        - {key}: \"{value[:50]}...\" ({len(value)} chars)")
            else:
                print(f"        - {key}: {type(value).__name__}")
    
    # Count unique exercises/units/lessons if fields exist
    if has_exercise_id:
        unique_exercises = len(collection.distinct("exercise_id"))
        print(f"\n      Unique exercises: {unique_exercises:,}")
    
    if has_questionId and collection.count_documents({"exerciseId": {"$exists": True}}):
        unique_exercises_old = len(collection.distinct("exerciseId"))
        print(f"      Unique exercises (old format): {unique_exercises_old:,}")
    
    # Check for regions if course_id exists
    if collection.count_documents({"course_id": {"$exists": True}}):
        unique_courses = len(collection.distinct("course_id"))
        print(f"      Unique courses: {unique_courses:,}")


def inspect_scraped_questions_collection(collection):
    """Inspect scraped_questions collection (old format)"""
    print(f"\n   🔍 Scraped Questions Analysis:")
    
    total = collection.count_documents({})
    print(f"      Total questions: {total:,}")
    
    # Check for learning videos
    has_videos = collection.count_documents({"learning_videos": {"$exists": True, "$ne": []}})
    has_suggested = collection.count_documents({"suggested_videos": {"$exists": True, "$ne": []}})
    
    print(f"      Questions with learning_videos: {has_videos:,}")
    print(f"      Questions with suggested_videos: {has_suggested:,}")


def main():
    """Main inspection function"""
    print("\n" + "="*80)
    print("MongoDB Database Inspector")
    print("="*80)
    
    # Get MongoDB URI
    mongodb_uri = os.getenv('MONGODB_URI')
    
    if not mongodb_uri:
        print("\n❌ MONGODB_URI not found in environment variables")
        print("   Please set MONGODB_URI in your .env file or environment")
        print("\n   Example:")
        print("   MONGODB_URI=mongodb://localhost:27017/")
        print("   # or")
        print("   MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/")
        return
    
    # Extract base URI (without database name)
    if '/' in mongodb_uri:
        # Remove database name if present
        base_uri = '/'.join(mongodb_uri.rsplit('/', 1)[:-1]) if mongodb_uri.count('/') > 2 else mongodb_uri.rsplit('/', 1)[0]
    else:
        base_uri = mongodb_uri
    
    print(f"\n🔗 Connecting to MongoDB...")
    print(f"   URI: {base_uri}")
    
    try:
        # Connect to MongoDB
        client = MongoClient(base_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("   ✅ Connected successfully\n")
        
        # List all databases
        db_names = client.list_database_names()
        print(f"📊 Available Databases: {len(db_names)}")
        print(f"   {', '.join(sorted(db_names))}\n")
        
        # Inspect specific databases
        databases_to_inspect = ['ai_tutor', 'questions_db', 'khan_academy', 'khan_academy_test']
        
        found_any = False
        for db_name in databases_to_inspect:
            if db_name in db_names:
                found_any = True
                inspect_database(client, db_name)
        
        # If none of the expected databases exist, show all
        if not found_any:
            print("\n⚠️  None of the expected databases (ai_tutor, questions_db) were found.")
            print("   Inspecting all available databases instead:\n")
            for db_name in sorted(db_names):
                if db_name not in ['admin', 'config', 'local']:  # Skip system databases
                    inspect_database(client, db_name)
        
        # Summary comparison
        print(f"\n{'='*80}")
        print("SUMMARY COMPARISON")
        print(f"{'='*80}\n")
        
        if 'ai_tutor' in db_names:
            ai_tutor_db = client['ai_tutor']
            ai_tutor_questions = ai_tutor_db.questions.count_documents({}) if 'questions' in ai_tutor_db.list_collection_names() else 0
            ai_tutor_scraped = ai_tutor_db.scraped_questions.count_documents({}) if 'scraped_questions' in ai_tutor_db.list_collection_names() else 0
            print(f"📊 ai_tutor database:")
            print(f"   - questions collection: {ai_tutor_questions:,} documents")
            print(f"   - scraped_questions collection: {ai_tutor_scraped:,} documents")
        
        if 'questions_db' in db_names:
            questions_db = client['questions_db']
            questions_count = questions_db.questions.count_documents({}) if 'questions' in questions_db.list_collection_names() else 0
            courses_count = questions_db.courses.count_documents({}) if 'courses' in questions_db.list_collection_names() else 0
            exercises_count = questions_db.exercises.count_documents({}) if 'exercises' in questions_db.list_collection_names() else 0
            print(f"\n📊 questions_db database:")
            print(f"   - questions collection: {questions_count:,} documents")
            print(f"   - courses collection: {courses_count:,} documents")
            print(f"   - exercises collection: {exercises_count:,} documents")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Error connecting to MongoDB: {e}")
        print("\nTroubleshooting:")
        print("1. Check your MONGODB_URI is correct")
        print("2. Ensure MongoDB is running (if local)")
        print("3. Check network connectivity (if Atlas)")
        print("4. Verify credentials are correct")
        return


if __name__ == "__main__":
    main()