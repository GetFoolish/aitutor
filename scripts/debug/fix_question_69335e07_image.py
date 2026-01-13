from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_image(question_id):
    print(f"Fixing image for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        print("Question not found.")
        return

    # Update correct key
    update_key = "question.widgets.image 1.options.backgroundImage.url"
    new_url = "/assets/images/replacements/uploaded_image_1768253222852.png"
    
    result = mongo_db.scraped_questions.update_one(
        {"_id": question["_id"]},
        {"$set": {update_key: new_url}}
    )
    
    if result.modified_count > 0:
        print(f"Successfully updated image URL to: '{new_url}'")
    else:
        print("Update failed or no changes made (URL might match existing).")

if __name__ == "__main__":
    fix_image("69335e0746bd2cf873ae9d92")
