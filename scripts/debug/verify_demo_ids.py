"""
Verify Demo Question IDs in MongoDB
Checks if the specific ObjectIDs used in the video demo exist in scraped_questions collection.
"""
import sys
import os
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

# Demo IDs from video script
DEMO_IDS = [
    "691c6d6a41372912898cd7ae",  # Chart Labels
    "691c6e2f41372912898cd98d",  # Compare View
    "691c693241372912898ccd8b",  # Formatting
    "691c6ace41372912898cd1fb",  # Font Size
    "691c6d7741372912898cd7d5",  # Widget Bug
]

def verify_question_ids():
    """Check if each demo ID exists in MongoDB."""
    print("=" * 60)
    print("VERIFYING DEMO QUESTION IDs IN MONGODB")
    print("=" * 60)
    print()
    
    results = []
    
    for question_id in DEMO_IDS:
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(question_id):
                results.append((question_id, "❌ INVALID", "Not a valid ObjectId format"))
                continue
            
            # Query MongoDB
            doc = mongo_db.scraped_questions.find_one(
                {'_id': ObjectId(question_id)},
                {'slug': 1, 'skill_prefix': 1}  # Only fetch minimal fields
            )
            
            if doc:
                slug = doc.get('slug', 'N/A')
                skill = doc.get('skill_prefix', 'N/A')
                results.append((question_id, "✅ EXISTS", f"Slug: {slug}, Skill: {skill}"))
            else:
                results.append((question_id, "❌ NOT FOUND", "No document with this ID"))
                
        except Exception as e:
            results.append((question_id, "❌ ERROR", str(e)))
    
    # Print results
    print(f"{'ObjectID':<30} {'Status':<15} {'Details'}")
    print("-" * 80)
    
    for obj_id, status, details in results:
        print(f"{obj_id:<30} {status:<15} {details}")
    
    print()
    print("=" * 60)
    
    # Summary
    exists_count = sum(1 for _, status, _ in results if "EXISTS" in status)
    total_count = len(results)
    
    print(f"SUMMARY: {exists_count}/{total_count} IDs found in MongoDB")
    
    if exists_count == total_count:
        print("✅ ALL DEMO IDs VERIFIED - Ready for video recording!")
    else:
        print("⚠️  SOME IDs MISSING - These are served from MOCK_QUESTIONS instead")
    
    print("=" * 60)
    
    return exists_count == total_count

if __name__ == "__main__":
    try:
        success = verify_question_ids()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ VERIFICATION FAILED: {e}")
        sys.exit(1)
