
import os
import sys
import json
from bson import ObjectId

# Add project root to path
original_cwd = os.getcwd()
project_root = original_cwd
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services', 'athenaAPI'))

try:
    from managers.mongodb_manager import mongo_db
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

id_str = "6937429984e723ebfd1227ca"
new_image_url = "/assets/images/questions/69374299/proportional_graph.png"

try:
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str}) or \
          mongo_db.scraped_questions.find_one({"questionId": id_str})
    
    if not doc:
        print("❌ FAILURE: Question not found in database.")
        sys.exit(1)

    # Update question widget
    question = doc.get('question', {})
    widgets = question.get('widgets', {})
    image_1 = widgets.get('image 1', {})
    
    if image_1:
        if 'options' not in image_1: image_1['options'] = {}
        if 'backgroundImage' not in image_1['options']: image_1['options']['backgroundImage'] = {}
        image_1['options']['backgroundImage']['url'] = new_image_url
        print("Updated question image 1")

    # Update hints
    hints = doc.get('hints', [])
    for i, hint in enumerate(hints):
        hint_widgets = hint.get('widgets', {})
        h_image_1 = hint_widgets.get('image 1', {})
        if h_image_1:
            if 'options' not in h_image_1: h_image_1['options'] = {}
            if 'backgroundImage' not in h_image_1['options']: h_image_1['options']['backgroundImage'] = {}
            h_image_1['options']['backgroundImage']['url'] = new_image_url
            print(f"Updated hint {i} image 1")

    # Save back to database
    result = mongo_db.scraped_questions.update_one(
        {"_id": doc['_id']},
        {"$set": {
            "question.widgets": widgets,
            "hints": hints
        }}
    )
    
    if result.modified_count > 0:
        print(f"✅ SUCCESS: Updated question {id_str} in database.")
    else:
        print("⚠️ No changes made to the database.")

except Exception as e:
    print(f"🔥 ERROR during database update: {e}")
    import traceback
    traceback.print_exc()
