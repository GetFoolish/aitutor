
import os
import sys
from bson import ObjectId

# Add project root to path
# The script is in aitutor/
project_root = os.getcwd()
sys.path.insert(0, project_root)
# Add services/athenaAPI to path for 'app' imports
sys.path.insert(0, os.path.join(project_root, 'services', 'athenaAPI'))

from managers.mongodb_manager import mongo_db
from app.question_loader import get_question_by_id

id_str = '691c6d6a41372912898cd7ae'
print(f"RUNNING INTERNAL DEBUG FOR ID: {id_str}")

try:
    result = get_question_by_id(id_str)
    if result:
        print("✅ SUCCESS: get_question_by_id returned a result.")
        print(f"KEYS: {list(result.keys())}")
        if 'perseusItem' in result:
             print("✅ perseusItem IS PRESENT.")
             p = result['perseusItem']
             print(f"PERSEUS ITEM KEYS: {list(p.keys())}")
             print(f"QUESTION CONTENT: {p['question'].get('content', '')[:100]}...")
    else:
        print("❌ FAILURE: get_question_by_id returned None.")
except Exception as e:
    print(f"🔥 CRASH during get_question_by_id: {e}")
    import traceback
    traceback.print_exc()
