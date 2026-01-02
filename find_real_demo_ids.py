"""
Find Real Question IDs from MongoDB
Samples questions from scraped_questions collection to replace mock data.
"""
import sys
import os
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_real_question_ids():
    """Find real question IDs from MongoDB for demo purposes."""
    print("=" * 80)
    print("SEARCHING FOR REAL QUESTION IDs IN MONGODB")
    print("=" * 80)
    print()
    
    # Target widget types for demo
    target_widgets = {
        'interactive-graph': 'Chart/Graph questions',
        'image': 'Image-based questions',
        'numeric-input': 'Numeric input questions',
        'dropdown': 'Dropdown questions',
        'radio': 'Multiple choice questions',
    }
    
    results = {}
    
    for widget_type, description in target_widgets.items():
        print(f"Searching for: {widget_type} ({description})...")
        
        try:
            # Query for questions with this widget type
            query = {
                '$or': [
                    # Top-level widgets
                    {f'question.widgets': {'$exists': True}},
                    # Nested structure
                    {'assessmentData.data.assessmentItem.item.itemData': {'$exists': True}},
                ]
            }
            
            # Sample a few questions
            pipeline = [
                {'$match': query},
                {'$sample': {'size': 10}},  # Get 10 random samples
            ]
            
            cursor = mongo_db.scraped_questions.aggregate(pipeline)
            
            found = False
            for doc in cursor:
                # Extract widgets
                widgets = {}
                question_data = doc.get('question', {})
                
                if isinstance(question_data, dict):
                    widgets = question_data.get('widgets', {})
                
                # Check if this question has the target widget type
                has_target = False
                for widget_id, widget_data in widgets.items():
                    if isinstance(widget_data, dict):
                        if widget_data.get('type') == widget_type:
                            has_target = True
                            break
                
                if has_target:
                    obj_id = str(doc['_id'])
                    slug = doc.get('slug', 'N/A')
                    skill = doc.get('skill_prefix', 'N/A')
                    
                    results[widget_type] = {
                        'id': obj_id,
                        'slug': slug,
                        'skill': skill,
                        'description': description
                    }
                    
                    print(f"  ✅ Found: {obj_id} (Slug: {slug})")
                    found = True
                    break
            
            if not found:
                print(f"  ⚠️  No questions found with widget type: {widget_type}")
                
        except Exception as e:
            print(f"  ❌ Error searching for {widget_type}: {e}")
    
    print()
    print("=" * 80)
    print("SUMMARY OF FOUND QUESTION IDs")
    print("=" * 80)
    print()
    
    if results:
        print("Copy these IDs to replace MOCK_QUESTIONS in question_loader.py:")
        print()
        for widget_type, data in results.items():
            print(f"# {data['description']}")
            print(f'"{data["id"]}": {{  # {data["slug"]} ({data["skill"]})')
            print(f'    # Widget type: {widget_type}')
            print(f'}}')
            print()
        
        print(f"Total: {len(results)} real question IDs found")
    else:
        print("❌ No questions found in MongoDB!")
        print("   Your database might be empty or the connection failed.")
    
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    try:
        results = find_real_question_ids()
        sys.exit(0 if results else 1)
    except Exception as e:
        print(f"❌ SEARCH FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
