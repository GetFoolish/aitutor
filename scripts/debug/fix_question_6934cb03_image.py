from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_image(question_id):
    print(f"Fixing image for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        print("Question not found.")
        return

    # Update correct key for main question image
    update_key = "question.widgets.image 1.options.backgroundImage.url"
    new_url = "/assets/images/replacements/uploaded_image_1768257870112.png"
    
    result = mongo_db.scraped_questions.update_one(
        {"_id": question["_id"]},
        {"$set": {update_key: new_url}}
    )
    
    if result.modified_count > 0:
        print(f"Successfully updated image URL to: '{new_url}'")
    else:
        print("Update failed or no changes made (URL might match existing).")
        # Check if the widget exists
        widgets = question.get("question", {}).get("widgets", {})
        if "image 1" not in widgets:
             print("Warning: 'image 1' widget not found in question.")
             print("Available widgets:", widgets.keys())

if __name__ == "__main__":
    fix_image("6934cb0364942dd77a11246c")
