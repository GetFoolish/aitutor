from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId
import re

def fix_content(question_id):
    print(f"Fixing content for question with LaTeX bolding: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        print("Question not found.")
        return

    content = question.get("question", {}).get("content", "")
    print(f"Original content length: {len(content)}")
    
    # We need to undo the previous markdown bolding and apply LaTeX bolding.
    # Previous: "position, **$x$,**"  -> Target: "position, $\\boldsymbol{x}$," 
    # (Note: keeping comma outside math is standard, or inside if it was inside. 
    # content previously put comma inside bold: **$x$,**. 
    # Let's put comma outside bold but inside math? No, comma shouldn't be bolded usually unless text is bold.
    # User asked for "x, t and equation". 
    # Let's try to match the previous pattern exactly to replace it reliably.
    
    new_content = content
    
    # 1. Variable x
    # Current state likely: "position, **$x$,**"
    # Or "position, **$x$**," depending on how the comma was handled.
    # My previous script did: .replace("position, $x,$", "position, **$x$,**")
    # So it is: "position, **$x$,**"
    
    # Use replace for exact string match from previous state
    # We want: "position, $\\boldsymbol{x}$," 
    # (Wait, user just wants x bold. The comma doesn't need to be bold, but if it's part of the sentence structure...)
    # Let's stick to bolding the Math symbol.
    new_content = new_content.replace("position, **$x$,**", "position, $\\boldsymbol{x}$,")
    
    # Fallback if manual edit intervened or previous state format is slightly diff, try regex
    # new_content = re.sub(r"position, \*\*(\$x\$),\*\*", r"position, $\\boldsymbol{x}$,", new_content)
    
    # 2. Variable t
    # Current state: "time, **$t$,**"
    new_content = new_content.replace("time, **$t$,**", "time, $\\boldsymbol{t}$,")
    
    # 3. Equation
    # Current state: "**$x=(6\\,\\text{m/s})t+2\\,\\text{m}$**"
    # We want: "$\\boldsymbol{x=(6\\,\\text{m/s})t+2\\,\\text{m}}$"
    
    target_eq_old = "**$x=(6\\,\\text{m/s})t+2\\,\\text{m}$**"
    # We inject \boldsymbol{ ... }
    replacement_eq = "$\\boldsymbol{x=(6\\,\\text{m/s})t+2\\,\\text{m}}$"
    
    new_content = new_content.replace(target_eq_old, replacement_eq)
    
    # Just in case the previous script didn't run or was reverted, let's also handle the "clean" state
    # "position, $x,$" -> "position, $\\boldsymbol{x}$,"
    new_content = new_content.replace("position, $x,$", "position, $\\boldsymbol{x}$,")
    new_content = new_content.replace("time, $t,$", "time, $\\boldsymbol{t}$,")
    
    target_eq_clean = "$x=(6\\,\\text{m/s})t+2\\,\\text{m}$"
    if target_eq_clean in new_content and target_eq_old not in new_content:
         # It wasn't bolded before? or we just replaced the bolded one?
         # If replace succeeded above, target_eq_old is gone.
         # But if we are running on fresh data, target_eq_clean is there.
         # So safe to replace target_eq_clean with replacement_eq IF we haven't already replaced it (which we might have if we stripped bold markers).
         # Actually, the string replacement logic is robust enough.
         # But wait, replacement_eq contains target_eq_clean content inside \boldsymbol.
         pass
         
    # Let's just double check if the equation needs bolding
    if target_eq_clean in new_content and "\\boldsymbol" not in new_content:
         new_content = new_content.replace(target_eq_clean, replacement_eq)

    if new_content != content:
        result = mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {"question.content": new_content}}
        )
        if result.modified_count > 0:
            print("Successfully updated question content in MongoDB with LaTeX bolding.")
            print("New content snippet:")
            # print surrounding vars
            start = new_content.find("position,")
            print(new_content[start:start+100])
            start_eq = new_content.find("$\\boldsymbol{x=")
            print(new_content[start_eq:start_eq+100])
        else:
            print("Update failed or no changes made (DB side).")
    else:
        print("No changes needed (content match not found).")
        print("Current content dump:")
        print(content)

if __name__ == "__main__":
    fix_content("6930d1b80f4b024e7c5dae25")
