
import sys
import os
from bson import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def search_special_widgets():
    print("SEARCHING FOR SPECIALIZED WIDGETS...")
    
    widgets_to_find = ['molecule', 'music-notation', 'cs-program', 'map', 'timeline']
    found = {}

    for widget in widgets_to_find:
        print(f"Searching for {widget}...")
        query = {
            '$or': [
                {f'question.widgets': {'$exists': True}},
                {'assessmentData.data.assessmentItem.item.itemData': {'$exists': True}}
            ]
        }
        
        # Limit to avoid timeout, but look deep
        cursor = mongo_db.scraped_questions.find(query).limit(5000)
        
        for doc in cursor:
            widgets = {}
            if 'question' in doc and 'widgets' in doc['question']:
                widgets = doc['question']['widgets']
            elif 'assessmentData' in doc:
                try:
                    widgets = doc['assessmentData']['data']['assessmentItem']['item']['itemData']['question']['widgets']
                except:
                    pass
            
            for k, v in widgets.items():
                if v.get('type') == widget:
                    obj_id = str(doc['_id'])
                    found[widget] = obj_id
                    print(f"  ✅ Found {widget}: {obj_id}")
                    break
            
            if widget in found:
                break
        
        if widget not in found:
            print(f"  ❌ {widget} NOT FOUND in first 5000 records")

if __name__ == "__main__":
    search_special_widgets()
