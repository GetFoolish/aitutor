
import os
import sys
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def search_other_animals():
    animals = ["dog", "cat", "bird", "fish", "horse", "cow", "pig", "sheep", "duck", "chicken", "lion", "tiger", "bear", "elephant", "giraffe", "monkey", "penguin", "turtle", "frog", "butterfly", "bee", "ant"]
    regex_pattern = "|".join(animals)
    
    results = list(mongo_db.scraped_questions.find({"question.widgets": {"$regex": regex_pattern, "$options": "i"}}))
    print(f"Found {len(results)} questions with potential animals.")
    
    found_keywords = set()
    for doc in results:
        widgets = doc.get('question', {}).get('widgets', {})
        for w_data in widgets.values():
            opt = w_data.get('options', {})
            alt = ""
            if w_data.get('type') == 'image':
                alt = opt.get('alt', '')
            elif w_data.get('type') == 'radio':
                choices = opt.get('choices', [])
                for c in choices:
                    match = re.search(r'!\[([^\]]*)\]', c.get('content', ''))
                    if match:
                        alt += " " + match.group(1)
            
            for animal in animals:
                if re.search(r'\b' + animal + r's?\b', alt, re.I):
                    found_keywords.add(animal)
    
    print(f"Animals actually found in alt texts: {sorted(list(found_keywords))}")

if __name__ == "__main__":
    search_other_animals()
