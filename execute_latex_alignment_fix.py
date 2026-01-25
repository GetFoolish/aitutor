import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=90000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

def fix_latex(text):
    if not isinstance(text, str):
        return text
        
    # We want to replace \begin{align} ... \end{align}
    # with \begin{array}{r} ... \end{array}
    # And handle common alignment operators
    
    # 1. Start tag
    text = re.sub(r"\\begin\{align\}", r"\\begin{array}{r}", text)
    # 2. End tag
    text = re.sub(r"\\end\{align\}", r"\\end{array}", text)
    
    # 3. Handle the alignment operator '&'
    # In 'array{r}', we don't strictly need the '&' if it's just one column, 
    # but Perseus sometimes puts it at the END: '123& \\' 
    # to signify "right align this line relative to others".
    # In array-right, we can just remove it if it's followed by line breaks
    text = re.sub(r"&\s*\\\\", r" \\\\", text)
    
    return text

def recursive_fix(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k == 'itemData' and isinstance(v, str):
                try:
                    inner_data = json.loads(v)
                    fixed_inner = recursive_fix(inner_data)
                    new_obj[k] = json.dumps(fixed_inner, ensure_ascii=False)
                except:
                    new_obj[k] = fix_latex(v)
            elif isinstance(v, str):
                new_obj[k] = fix_latex(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    else:
        return obj

COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print("Starting GLOBAL LaTeX alignment fix (align -> array{r})...")

# Search for any doc containing \begin{align}
cursor = collection.find({
    "$or": [
        {"question.content": {"$regex": r"\\begin\{align\}"}},
        {"assessmentData.data.assessmentItem.item.itemData": {"$regex": r"\\begin\{align\}"}}
    ]
})

total_updated = 0
for doc in cursor:
    fixed_doc = recursive_fix(doc)
    # Save back
    collection.replace_one({"_id": doc["_id"]}, fixed_doc)
    total_updated += 1
    if total_updated % 20 == 0:
        print(f"  Fixed {total_updated} docs...")

print(f"\nDONE. Total questions fixed: {total_updated}")
