import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']
question_id = "693199158189149cdbee41a8"

def fix_latex_magnitude(s):
    if not isinstance(s, str):
        return s
        
    # 1. Fix magnitude notation: convert any variation of double bars to \left\| ... \right\|
    # Specifically target the broken \left|\left| ... \right|=
    # We use regex to catch different amounts of backslashes (1, 2, or 4)
    
    # Replacement for 4 backslashes (inside double-nested JSON)
    s = s.replace('\\\\\\\\left|\\\\\\\\left|', '\\\\\\\\left\\\\|')
    s = s.replace('\\\\\\\\left| \\\\\\\\left|', '\\\\\\\\left\\\\|')
    
    # Replacement for 2 backslashes (standard JSON string)
    s = s.replace('\\\\left|\\\\left|', '\\\\left\\\\|')
    s = s.replace('\\\\left| \\\\left|', '\\\\left\\\\|')
    
    # Replacement for 1 backslash (raw string)
    s = s.replace('\\left|\\left|', '\\left\\|')
    s = s.replace('\\left| \\left|', '\\left\\|')

    # Close correctly
    # If we have \left\| but only one \right|, we must fix it
    # We search for \left\| followed by characters not including \right\| then followed by \right| and then not another |
    # But simpler: just replace \right| with \right\| when magnitude is present and it's missing the second bar
    
    # Target the specific broken sequence: \right|= or \right| =
    s = re.sub(r'(\\+right\|)\s*=', r'\1\\| =', s)
    # Also catch double-backslashed version
    s = re.sub(r'(\\\\+right\|)\s*=', r'\1\\\\| =', s)
    
    # Generally ensure \left\| and \right\| are pairs if possible
    # (This is safer than a blind global replace of \right|)
    
    # 2. Fix encoding Ôÿâ -> ☃
    s = s.replace("Ôÿâ", "☃")
    s = s.replace("\\u2603", "☃")
    
    return s

def process_object(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k == 'itemData' and isinstance(v, str):
                # This is the nested JSON string
                print("Found itemData, processing nested content...")
                try:
                    # Fix magnitude in the raw string FIRST
                    fixed_v = fix_latex_magnitude(v)
                    new_obj[k] = fixed_v
                except Exception as e:
                    print(f"Error fixing itemData: {e}")
                    new_obj[k] = v
            else:
                new_obj[k] = process_object(v)
        return new_obj
    elif isinstance(obj, list):
        return [process_object(i) for i in obj]
    elif isinstance(obj, str):
        return fix_latex_magnitude(obj)
    else:
        return obj

for coll_name in ['questions', 'dash_questions', 'scraped_questions']:
    coll = db[coll_name]
    item = coll.find_one({"_id": ObjectId(question_id)})
    if not item:
        item = coll.find_one({"_id": question_id})
    
    if item:
        print(f"Fixing {coll_name}...")
        fixed_item = process_object(item)
        coll.replace_one({"_id": item["_id"]}, fixed_item)
        print(f"Successfully updated {coll_name}")

print("DONE.")
