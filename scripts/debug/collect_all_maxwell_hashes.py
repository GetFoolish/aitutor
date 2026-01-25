import os
from pymongo import MongoClient
from bson import ObjectId
import json
import re

uri = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ai_tutor']

def collect_all_hashes():
    # Use first 30 chars of content as fingerprint
    fingerprint = "The diagram below shows the di"
    similar = db.scraped_questions.find({'question.content': {'$regex': f'^{re.escape(fingerprint)}', '$options': 'i'}})
    
    unique_sets = {}
    for q in similar:
        data_str = str(q)
        found = re.findall(r'ka-perseus-graphie/([0-9a-f]+)', data_str)
        if found:
            s = tuple(sorted(list(set(found))))
            if s not in unique_sets:
                unique_sets[s] = []
            unique_sets[s].append(str(q['_id']))
            
    print(f"Found {len(unique_sets)} unique hash sets:")
    for i, (s, ids) in enumerate(unique_sets.items()):
        print(f"\nSet {i}: {len(ids)} questions")
        print(f"Hashes: {list(s)}")
        # Dump one to see mapping
        q = db.scraped_questions.find_one({'_id': ObjectId(ids[0])})
        # Try to identify which hash is which
        mapping = {}
        # Main image
        main_img = q.get('question', {}).get('widgets', {}).get('image 1', {}).get('options', {}).get('backgroundImage', {}).get('url', '')
        if main_img:
            h = main_img.split('/')[-1]
            mapping['main'] = h
        # Radio choices
        choices = q.get('question', {}).get('widgets', {}).get('radio 1', {}).get('options', {}).get('choices', [])
        for j, c in enumerate(choices):
            content = c.get('content', '')
            found_h = re.search(r'ka-perseus-graphie/([0-9a-f]+)', content)
            if found_h:
                mapping[f'choice_{j}'] = found_h.group(1)
        
        # Hint 4 image
        hints = q.get('hints', [])
        if len(hints) >= 4:
             h4_img = hints[3].get('widgets', {}).get('image 1', {}).get('options', {}).get('backgroundImage', {}).get('url', '')
             if h4_img:
                 h = h4_img.split('/')[-1]
                 mapping['hint4'] = h
        
        print(f"Mapping: {json.dumps(mapping, indent=2)}")

if __name__ == "__main__":
    collect_all_hashes()
