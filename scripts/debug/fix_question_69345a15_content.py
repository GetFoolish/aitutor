from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_content(question_id):
    print(f"Fixing content for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        print("Question not found.")
        return

    content = question.get("question", {}).get("content", "")
    print(f"Original content length: {len(content)}")
    
    # Fix the unbalanced markdown in the intro
    # From: ***The Quest of the Silver Fleece* ...**
    # To: **_The Quest of the Silver Fleece_ ...**
    new_content = content.replace("***The Quest of the Silver Fleece*", "**_The Quest of the Silver Fleece_")
    
    # Ensure the final question is bold (it seems it already is, but let's be sure no trailing markup broke it)
    # The current final question is: **Which quotation from the text best shows what Mrs. Vanderpool believes to be the purpose of travel?**
    
    if new_content != content:
        result = mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {"question.content": new_content}}
        )
        if result.modified_count > 0:
            print("Successfully updated question content in MongoDB.")
        else:
            print("Update failed or no changes made.")
    else:
        print("No changes needed in MongoDB.")

if __name__ == "__main__":
    fix_content("69345a15bcfb8e91f4cdda1c")
