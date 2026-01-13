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
    
    # 1. Bolden x: "position, $x$," -> "position, **$x$,**" (including comma inside bold might be preferred, or just variable?)
    # The request image shows variable x inside blue underline. Usually variables are bolded.
    # Let's bold the variable: $x$ -> **$x$**
    new_content = content.replace("position, $x,$", "position, **$x$,**")
    
    # 2. Bolden t: "time, $t,$" -> "time, **$t$,**"
    new_content = new_content.replace("time, $t,$", "time, **$t$,**")
    
    # 3. Bolden equation: "$x=(6\\,\\text{m/s})t+2\\,\\text{m}$"
    # Search string from JSON: "$x=(6\\,\\text{m/s})t+2\\,\\text{m}$"
    # We replace it with: "**$x=(6\\,\\text{m/s})t+2\\,\\text{m}$**"
    
    # Be careful with escaping for find/replace. The string in Python source code needs to match.
    target_eq = "$x=(6\\,\\text{m/s})t+2\\,\\text{m}$"
    replacement_eq = "**$x=(6\\,\\text{m/s})t+2\\,\\text{m}$**"
    
    new_content = new_content.replace(target_eq, replacement_eq)

    if new_content != content:
        result = mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {"question.content": new_content}}
        )
        if result.modified_count > 0:
            print("Successfully updated question content in MongoDB.")
            print("New content preview:")
            print(new_content)
        else:
            print("Update failed or no changes made (DB side).")
    else:
        print("No changes needed (content match not found).")
        # specific debugging
        if "position, $x,$" not in content:
            print("Could not find 'position, $x,$'")
        if "time, $t,$" not in content:
             print("Could not find 'time, $t,$'")
        if target_eq not in content:
             print(f"Could not find equation: {target_eq}")

if __name__ == "__main__":
    fix_content("6930d1b80f4b024e7c5dae25")
