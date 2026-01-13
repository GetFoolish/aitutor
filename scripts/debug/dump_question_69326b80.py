
import os
import sys
import json
from bson import ObjectId
import datetime

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

id_str = "69326b802a4ca36772842d03"

try:
    doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str}) or \
          mongo_db.scraped_questions.find_one({"questionId": id_str})
    
    if not doc:
        print("❌ FAILURE: Question not found in database.")
    else:
        def json_serial(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            raise TypeError ("Type %s not serializable" % type(obj))

        with open(f"question_{id_str[:8]}.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, default=json_serial)
        print(f"✅ SUCCESS: Question dumped to question_{id_str[:8]}.json")

except Exception as e:
    print(f"🔥 CRASH during dump: {e}")
