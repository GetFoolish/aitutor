import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

target_ids = [
    "69309146e3928da5187fe3c4",
    "6931556dbd78eec1e54b51af",
    "6931ce2836979a821f00f0ff",
    "69332dde42728321ec258a53",
    "6933dad245a4cb2e2ed4454a",
    "69356eab2a2c00b355a23059",
    "6935a7a9541cdb343633dfaf",
    "6935e06835efbaf0a785d21a",
    "693619a9b6dab7b3d9e776dd",
    "6936542d4d5b9546f400db83",
    "6936ff69b753254d0bf6ff2c"
]

# The url we used for replacement
FIXED_IMAGE_URL = "/fixed_graphs/graph_6936f.png"

def remove_redundant_widgets(obj):
    if not isinstance(obj, dict):
        return obj
        
    widgets = obj.get('widgets', {})
    content = obj.get('content', '')
    
    if not widgets or not content:
        return obj
        
    updated_content = content
    redundant_widget_ids = []
    
    for widget_id, widget_data in widgets.items():
        if widget_data.get('type') == 'image':
            options = widget_data.get('options', {})
            bg_img = options.get('backgroundImage', {})
            url = bg_img.get('url', '')
            
            # We look for widgets that point to our fixed image
            if url == FIXED_IMAGE_URL:
                # Is it the "small" one?
                # Usually the main graph is the larger one in the box property or has certain alt text
                # But in this case, the user wants to remove the one that appears before the other
                # In the question: [[☃ image 1]] \n\n [[☃ image 2]]
                # Both index to the same URL now.
                
                # Heuristic: Remove the FIRST instance if there are two
                pass
                
    # Targeted string removal for the specific "James" question pattern
    # Remove the first [[☃ image X]] found in the question content if it's followed by another
    pattern = r"\[\[☃ image \d+\]\]"
    matches = list(re.finditer(pattern, updated_content))
    
    if len(matches) >= 2:
        print(f"Found {len(matches)} image widgets, removing the first one...")
        first_match = matches[0]
        # Remove the first match and any surrounding whitespace
        updated_content = updated_content[:first_match.start()].rstrip() + "\n\n" + updated_content[first_match.end():].lstrip()
    
    obj['content'] = updated_content
    return obj

def process_item(item):
    # Process main question
    if 'question' in item:
        item['question'] = remove_redundant_widgets(item['question'])
        
    # Process hints - skip for now as hints might need the small icon in the text 
    # (e.g. "Each [Box] = 3")
    # Actually, if I replaced the small box URL with the fixed graph, the hints are also broken.
    
    # Process assessmentData itemData
    if 'assessmentData' in item:
        try:
            item_data_str = item['assessmentData']['data']['assessmentItem']['item']['itemData']
            item_data = json.loads(item_data_str)
            
            # Question in itemData
            if 'question' in item_data:
                item_data['question'] = remove_redundant_widgets(item_data['question'])
            
            # Restore the small icons in hints if they were replaced by mistake?
            # Better to just keep my replacement but avoid the double-image in the question.
            
            item['assessmentData']['data']['assessmentItem']['item']['itemData'] = json.dumps(item_data, ensure_ascii=False)
        except Exception as e:
             print(f"Error processing itemData: {e}")
             
    return item

COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print(f"Removing redundant icon widgets for {len(target_ids)} IDs...")

updated_count = 0
for q_id in target_ids:
    print(f"Processing {q_id}...")
    item = collection.find_one({"_id": ObjectId(q_id)}) or collection.find_one({"_id": q_id})
    if item:
        fixed_item = process_item(item)
        collection.replace_one({"_id": item["_id"]}, fixed_item)
        updated_count += 1

print(f"Finished. Updated {updated_count} questions.")
