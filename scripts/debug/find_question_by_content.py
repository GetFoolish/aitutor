from managers.mongodb_manager import mongo_db
import re

def find_question():
    print("Searching for questions with 'explanation' widgets in hints...")
    
    # Iterate all questions (filtering in python is easier than deep nesting queries sometimes)
    # But for speed, let's try a query
    cursor = mongo_db.scraped_questions.find({})
    
    count = 0
    found_any = False
    
    for q in cursor:
        hints = q.get('hints', [])
        for i, hint in enumerate(hints):
            widgets = hint.get('widgets', {})
            for w_name, w_data in widgets.items():
                if w_data.get('type') == 'explanation':
                    print(f"[{count+1}] Found Question ID: {q['_id']}")
                    print(f"  Hint {i+1} has explanation widget: {w_name}")
                    print(f"  Content: {hint['content'][:100]}...")
                    found_any = True
                    # Check if 'g = 4' is in content
                    if 'g = 4' in hint['content'] or 'g=4' in hint['content']:
                        print("  MATCHES 'g = 4' TEXT!")
                    return # Stop after first detailed find
        count += 1
        if count % 100 == 0:
            print(f"Checked {count} questions...")
            
    if not found_any:
        print("No explanation widgets found in hints.")

if __name__ == "__main__":
    find_question()
