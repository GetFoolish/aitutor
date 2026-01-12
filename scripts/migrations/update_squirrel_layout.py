from managers.mongodb_manager import mongo_db
from bson import ObjectId
import re

def migrate():
    q_id = '69332dbf42728321ec258a4d'
    q = mongo_db.scraped_questions.find_one({'_id': ObjectId(q_id)})
    
    if not q:
        print(f"Question {q_id} not found")
        return

    content = q['question']['content']
    widgets = q['question']['widgets']
    
    # 1. Remove [[☃ image 1]] (Legend)
    # The content has: "The picture graph below shows ...\n\n[[☃ image 1]]\n\n[[☃ image 2]]\n\n..."
    # We want to remove [[☃ image 1]] and extra newlines
    
    print("Original Content length:", len(content))
    
    # Regex to remove image 1 placeholder and surrounding whitespace
    # Handles [[ \u2603 image 1 ]] with optional spaces
    new_content = re.sub(r'\n*\s*\[\[\u2603 image 1\]\]\s*\n*', '\n\n', content)
    
    # Ensure we didn't accidentally merge too much
    # We want "The picture graph ...\n\n[[☃ image 2]]..."
    
    print("New Content length:", len(new_content))
    
    # 2. Resize and Center Image 2 (Graph)
    if 'image 2' in widgets:
        print("Updating image 2 dimensions...")
        opts = widgets['image 2']['options']
        # Set to uploaded image dimensions 726x651
        opts['backgroundImage']['width'] = 726
        opts['backgroundImage']['height'] = 651
        # Ensure alignment is block (centers it)
        widgets['image 2']['alignment'] = 'block'
        
        # Also clean up box size if used?
        opts['box'] = [726, 651]
        
    else:
        print("Warning: image 2 widget not found")

    mongo_db.scraped_questions.update_one(
        {'_id': ObjectId(q_id)},
        {'$set': {
            'question.content': new_content,
            'question.widgets': widgets
        }}
    )
    print("Successfully updated layout.")

if __name__ == "__main__":
    migrate()
