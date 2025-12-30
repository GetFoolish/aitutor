#!/usr/bin/env python3
"""
Quick script to check what's in MongoDB cloud database
"""
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from managers.mongodb_manager import MongoDBManager

def main():
    mongo = MongoDBManager()
    
    print("\n" + "="*80)
    print("CHECKING MONGODB CLOUD DATA")
    print("="*80)
    
    # Check questions_db database
    print("\n📊 questions_db collections:")
    print("-" * 80)
    
    collections = {
        'courses': mongo.courses,
        'units': mongo.units,
        'lessons': mongo.lessons,
        'exercises': mongo.exercises,
        'questions': mongo.questions
    }
    
    for name, collection in collections.items():
        try:
            count = collection.count_documents({})
            print(f"  {name:15} {count:,} documents")
            
            # Show sample for questions
            if name == 'questions' and count > 0:
                sample = collection.find_one()
                if sample:
                    print(f"    Sample fields: {list(sample.keys())[:10]}")
        except Exception as e:
            print(f"  {name:15} ERROR: {e}")
    
    # Check if Math courses exist
    print("\n🔍 Math courses check:")
    print("-" * 80)
    math_courses = list(mongo.courses.find({"region": "US"}).limit(5))
    print(f"  Found {len(math_courses)} US courses (showing first 5)")
    for course in math_courses:
        print(f"    - {course.get('title', 'Unknown')}")
    
    print("\n" + "="*80)
    print("✅ MongoDB connection working!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
