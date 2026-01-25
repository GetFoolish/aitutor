import os
from pymongo import MongoClient
from bson import ObjectId
import json
from datetime import datetime

uri = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ai_tutor']

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def dump_question(qid):
    print(f"Dumping question: {qid}")
    q = db.scraped_questions.find_one({'_id': ObjectId(qid)})
    if not q:
        q = db.scraped_questions.find_one({'_id': qid})
        
    if q:
        # Convert ObjectId to string
        q['_id'] = str(q['_id'])
        
        # Print main content parts
        content = q.get('question', {}).get('content', '')
        print("\n--- CONTENT ---")
        print(content)
        print("--- END CONTENT ---\n")
        
        widgets = q.get('question', {}).get('widgets', {})
        print(f"Widgets: {list(widgets.keys())}")
        for w_id, w_data in widgets.items():
            print(f"  {w_id}: {w_data.get('type')}")
        
        hints = q.get('hints', [])
        print(f"\nNum Hints: {len(hints)}")
        for i, h in enumerate(hints):
            print(f"  Hint {i+1} widgets: {list(h.get('widgets', {}).keys())}")
            if 'plotter' in str(h.get('content', '')):
                print(f"  Hint {i+1} contains plotter reference!")

        filename = f"question_{qid[:8]}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(q, f, indent=2, ensure_ascii=False, default=json_serial)
        print(f"\nSaved full data to {filename}")
        
        # Search for similar questions
        # Use first 30 chars of content as fingerprint
        fingerprint = content[:30]
        if fingerprint:
            print(f"Searching for similar questions with fingerprint: {fingerprint}...")
            similar = db.scraped_questions.find({'question.content': {'$regex': f'^{re.escape(fingerprint)}', '$options': 'i'}})
            ids = [str(s['_id']) for s in similar]
            print(f"Found {len(ids)} similar questions: {ids}")
    else:
        print("Question not found")

import re

if __name__ == "__main__":
    dump_question("6936dfa77b73663f0e7752d5")
