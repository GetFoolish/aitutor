from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_caption(question_id):
    print(f"Fixing caption for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        print("Question not found.")
        return

    # Check "image 1" widget specifically, or iterate all
    widgets = question.get("question", {}).get("widgets", {})
    image_widget = widgets.get("image 1")
    
    if not image_widget:
        print("Image widget 'image 1' not found.")
        return

    options = image_widget.get("options", {})
    caption = options.get("caption", "")
    
    print(f"Original caption: '{caption}'")
    
    if "*" in caption:
        new_caption = caption.replace("*", "")
        # Update specific field
        
        # We need to construct the update path.
        # It's inside question -> widgets -> image 1 -> options -> caption
        
        # However, because we are updating a nested dictionary key inside a JSON field (in some systems) or a nested document
        # In this mongo schema, 'question' seems to be a nested object.
        
        update_key = "question.widgets.image 1.options.caption"
        
        result = mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {update_key: new_caption}}
        )
        
        if result.modified_count > 0:
            print(f"Successfully updated caption to: '{new_caption}'")
        else:
            print("Update failed or no changes made.")
    else:
        print("No asterisks found in caption.")

if __name__ == "__main__":
    fix_caption("693539cde61eddfd0c726620")
