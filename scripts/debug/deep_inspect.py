
import os
import sys
import json
from bson import ObjectId

# Add project root to path
# The script is in aitutor/
project_root = os.getcwd()
sys.path.insert(0, project_root)
# Add services/athenaAPI to path for 'app' imports
sys.path.insert(0, os.path.join(project_root, 'services', 'athenaAPI'))

from managers.mongodb_manager import mongo_db
from app.question_loader import get_question_by_id

id_str = '692fac057e334152c5f473e5'
print(f"DEEP INSPECT FOR ID: {id_str}")

try:
    result = get_question_by_id(id_str)
    if result and 'perseusItem' in result:
        p = result['perseusItem']
        widgets = p['question'].get('widgets', {})
        print(f"TOTAL WIDGETS: {len(widgets)}")
        for w_id, w_data in widgets.items():
            w_type = w_data.get('type')
            print(f"  - Widget {w_id} ({w_type})")
            if w_type == 'interactive-graph':
                options = w_data.get('options', {})
                print(f"    - Options: {json.dumps(options, indent=2)}")
                bg = options.get('backgroundImage', {})
                url = bg.get('url')
                print(f"    - Background URL: {url}")
    else:
        print("❌ FAILURE: result or perseusItem missing.")
except Exception as e:
    print(f"🔥 CRASH during deep inspect: {e}")
