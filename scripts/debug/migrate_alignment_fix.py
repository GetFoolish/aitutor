from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_alignment(question_id):
    print(f"Fixing alignment for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": question_id})
    if not question:
        try:
            question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
            
    if not question:
        print("Question not found.")
        return

    content = question.get("question", {}).get("content", "")
    print(f"Original content: {repr(content)}")
    
    # Remove the newlines before the numeric-input
    # The current pattern is: "Constant of proportionality $ = $\n\n[[☃ numeric-input 1]]"
    new_content = content.replace("$\n\n[[", "$ [[")
    new_content = new_content.replace("$ = $\n\n[[", "$ = $ [[")
    
    if new_content == content:
        # Fallback for other potential newline combinations
        new_content = content.replace("=\n\n[[", "= [[")
        new_content = new_content.replace("=\n[[", "= [[")
        new_content = new_content.replace("$\n[[", "$ [[")

    print(f"New content: {repr(new_content)}")
    
    if new_content != content:
        result = mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {"question.content": new_content}}
        )
        if result.modified_count > 0:
            print("Successfully updated question content.")
        else:
            print("Update failed or no changes made.")
    else:
        print("No changes needed or pattern not found.")

if __name__ == "__main__":
    fix_alignment("6932a69125f2e0b37ec6039c")
