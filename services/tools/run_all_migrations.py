"""
Master Migration Script - Run All Phase 1 Migrations
Executes all 3 migration scripts in correct order
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def main():
    print("\n" + "="*80)
    print("PHASE 1: QUESTIONS MIGRATION TO MONGODB")
    print("="*80)
    print("\nThis will migrate:")
    print("  1. Skills (27 skills)")
    print("  2. DASH Questions (~50-60 questions)")
    print("  3. Perseus Questions (4,835 questions)")
    print("\nNOTE: Local files will NOT be deleted (kept as backup)")
    print("="*80)
    
    response = input("\nProceed with migration? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n❌ Migration cancelled.")
        return
    
    print("\n" + "="*80)
    print("STARTING MIGRATION...")
    print("="*80 + "\n")
    
    # Import migration functions
    try:
        from migrate_skills_to_mongodb import migrate_skills
        from migrate_dash_questions_to_mongodb import migrate_dash_questions
        from migrate_perseus_to_mongodb import migrate_perseus_questions
    except ImportError as e:
        print(f"❌ Failed to import migration scripts: {e}")
        print("\nMake sure you are running this from the 'scripts' directory or project root.")
        return
    
    # Step 1: Migrate Skills
    print("\n" + "🔹"*40)
    print("STEP 1/3: Migrating Skills...")
    print("🔹"*40 + "\n")
    try:
        if not migrate_skills():
            print("\n❌ Skills migration failed!")
            return
    except Exception as e:
        print(f"\n❌ Skills migration error: {e}")
        return
    
    # Step 2: Migrate DASH Questions
    print("\n" + "🔹"*40)
    print("STEP 2/3: Migrating DASH Questions...")
    print("🔹"*40 + "\n")
    try:
        if not migrate_dash_questions():
            print("\n❌ DASH questions migration failed!")
            return
    except Exception as e:
        print(f"\n❌ DASH questions migration error: {e}")
        return
    
    # Step 3: Migrate Perseus Questions
    print("\n" + "🔹"*40)
    print("STEP 3/3: Migrating Perseus Questions...")
    print("🔹"*40 + "\n")
    try:
        if not migrate_perseus_questions():
            print("\n❌ Perseus questions migration failed!")
            return
    except Exception as e:
        print(f"\n❌ Perseus questions migration error: {e}")
        return
    
    # Success!
    print("\n" + "="*80)
    print("✅ ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
    print("="*80)
    print("\nNext Steps:")
    print("  1. Run: python scripts/test_mongodb_data.py")
    print("  2. Update code to use MongoDB")
    print("  3. Test the system")
    print("  4. Keep local files as backup")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

