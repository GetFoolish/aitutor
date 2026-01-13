
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

id_str = "693572b62a2c00b355a230d6"

def update_widget_options(widget, new_url):
    if widget.get('type') == 'image':
        if 'options' not in widget:
            widget['options'] = {}
        if 'backgroundImage' not in widget['options']:
            widget['options']['backgroundImage'] = {}
        widget['options']['backgroundImage']['url'] = new_url
    return widget

try:
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str}) or \
          mongo_db.scraped_questions.find_one({"questionId": id_str})
    
    if not doc:
        print("❌ FAILURE: Question not found in database.")
        sys.exit(1)

    # Update choices in radio 1
    question = doc.get('question', {})
    widgets = question.get('widgets', {})
    radio_1 = widgets.get('radio 1', {})
    
    if radio_1 and radio_1.get('type') == 'radio':
        choices = radio_1.get('options', {}).get('choices', [])
        
        # Mapping URLs in choices
        # Choice 0: Scale 120
        # Choice 1: Scale 40
        # Choice 2: Scale 20
        choice_urls = [
            "/assets/images/questions/693572b6/scale_120.png",
            "/assets/images/questions/693572b6/scale_40.png",
            "/assets/images/questions/693572b6/scale_20.png"
        ]
        
        for i, url in enumerate(choice_urls):
            if i < len(choices):
                content = choices[i].get('content', '')
                # Replace the markdown image URL
                import re
                choices[i]['content'] = re.sub(r'!\[.*?\]\(.*?\)', f'![Graphie Image]({url})', content)
                print(f"Updated Choice {i} content")

    # Update hints
    hints = doc.get('hints', [])
    # Hint 1 (index 1 in hints list) -> scale 20 (too small)
    # Hint 2 (index 2 in hints list) -> scale 120 (too large)
    # Hint 3 (index 3 in hints list) -> scale 40 (works!)
    # Hint 4 (index 4 in hints list) -> scale 40 (final)
    
    hint_mapping = {
        1: "/assets/images/questions/693572b6/scale_20.png",
        2: "/assets/images/questions/693572b6/scale_120.png",
        3: "/assets/images/questions/693572b6/scale_40.png",
        4: "/assets/images/questions/693572b6/scale_40.png"
    }

    for hint_idx, url in hint_mapping.items():
        if hint_idx < len(hints):
            hint_widgets = hints[hint_idx].get('widgets', {})
            image_1 = hint_widgets.get('image 1', {})
            if image_1:
                hints[hint_idx]['widgets']['image 1'] = update_widget_options(image_1, url)
                print(f"Updated Hint {hint_idx} image 1")

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
        print("⚠️ No changes made to the database (document might be already updated).")

except Exception as e:
    print(f"🔥 ERROR during database update: {e}")
    import traceback
    traceback.print_exc()
