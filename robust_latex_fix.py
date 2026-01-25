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

def solve_latex(s):
    if not isinstance(s, str):
        return s
    
    # 1. Standardize magnitude to \left\Vert ... \right\Vert
    # This is much safer than \| or ||
    
    # Handle all previous variations (even the broken ones)
    # Start with the most broken ones from my previous attempt
    s = s.replace(r"\right|\|", r"\right\Vert")
    s = s.replace(r"\right\||", r"\right\Vert")
    s = s.replace(r"\right\=", r"\right\Vert =")
    
    # Standardize all magnitude opens
    s = re.sub(r'\\+left\|\\+left\|', r'\\left\\Vert ', s)
    s = re.sub(r'\\+left\| \|', r'\\left\\Vert ', s)
    s = re.sub(r'\\+left\\\|', r'\\left\\Vert ', s)
    s = re.sub(r'\\+left\|(?![a-zA-Z])', r'\\left\\Vert ', s) # If it's a single bar but likely meant to be magnitude
    
    # Correct magnitude closes
    # Look for \right| followed by something or end, but only if we have \left\Vert
    if r"\left\Vert" in s:
        s = re.sub(r'\\+right\|\\+right\|', r'\\right\\Vert ', s)
        s = re.sub(r'\\+right\|', r'\\right\\Vert ', s)
        s = re.sub(r'\\+right\\\|', r'\\right\\Vert ', s)
    
    # Specific case for the magnitudes in this question
    s = s.replace(r"||c\cdot \vec v||", r"\left\Vert c\cdot \vec v \right\Vert")
    s = s.replace(r"|| \vec v ||", r"\left\Vert \vec v \right\Vert")
    s = s.replace(r"||\vec v||", r"\left\Vert \vec v \right\Vert")
    
    # 2. Fix snowflake encoding
    s = s.replace("Ôÿâ", "☃")
    s = s.replace("\\u2603", "☃")
    
    # 3. Final cleanup - ensure no triple escapes or weird spaces
    s = s.replace(r"\Vert \Vert", r"\Vert")
    s = s.replace(r"\Vert =", r"\Vert =")
    
    return s

def recursive_fix(obj):
    if isinstance(obj, dict):
        return {k: recursive_fix(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    elif isinstance(obj, str):
        return solve_latex(obj)
    else:
        return obj

for coll_name in ['questions', 'dash_questions', 'scraped_questions']:
    coll = db[coll_name]
    item = coll.find_one({"_id": ObjectId(question_id)})
    if not item:
        item = coll.find_one({"_id": question_id})
    
    if item:
        print(f"Applying robust fix to {coll_name}...")
        
        # Special handling for itemData string if it exists
        try:
            item_data = item.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if item_data:
                fixed_item_data = solve_latex(item_data)
                item['assessmentData']['data']['assessmentItem']['item']['itemData'] = fixed_item_data
        except:
            pass
            
        # Fix all other fields
        fixed_item = recursive_fix(item)
        
        coll.replace_one({"_id": item["_id"]}, fixed_item)
        print(f"Updated {coll_name}")

print("Verification check on scraped_questions content...")
final_check = db['scraped_questions'].find_one({"_id": question_id}) or db['scraped_questions'].find_one({"_id": ObjectId(question_id)})
if final_check:
    print(f"Content: {repr(final_check['question']['content'])}")
