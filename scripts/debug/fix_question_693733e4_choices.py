import json
import os
import sys

# Add project root to path to allow importing managers
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_question_693733e4():
    question_id = "693733e4d416931ff461ba00"
    print(f"Fixing choices for question: {question_id}")
    
    doc = mongo_db.scraped_questions.find_one({"_id": question_id})
    if not doc:
        try:
            doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
            
    if not doc:
        print("Question not found.")
        return

    def clean_content(content):
        if not content:
            return content
        # Remove any existing backticks first
        cleaned = content.strip()
        while cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1].strip()
        
        # Wrap in single backticks for proper rendering in our new widget
        return f"`{cleaned}`"

    modified = False

    # 1. Update main question radio choices
    if "question" in doc and "widgets" in doc["question"]:
        widgets = doc["question"]["widgets"]
        for widget_name, widget_data in widgets.items():
            if widget_data.get("type") == "radio":
                choices = widget_data.get("options", {}).get("choices", [])
                for choice in choices:
                    old_content = choice.get("content", "")
                    new_content = clean_content(old_content)
                    if old_content != new_content:
                        print(f"Updating choice content from '{old_content}' to '{new_content}'")
                        choice["content"] = new_content
                        modified = True

    # 2. Update perseusItem question radio choices
    if "perseusItem" in doc and "question" in doc["perseusItem"]:
        widgets = doc["perseusItem"]["question"].get("widgets")
        if widgets:
            for widget_name, widget_data in widgets.items():
                if widget_data.get("type") == "radio":
                    choices = widget_data.get("options", {}).get("choices", [])
                    for choice in choices:
                        old_content = choice.get("content", "")
                        new_content = clean_content(old_content)
                        if old_content != new_content:
                            print(f"Updating perseusItem choice content from '{old_content}' to '{new_content}'")
                            choice["content"] = new_content
                            modified = True

    # 3. Update itemData (stringified JSON)
    if "itemData" in doc and doc["itemData"]:
        try:
            item_data = json.loads(doc["itemData"])
            item_modified = False
            if "question" in item_data and "widgets" in item_data["question"]:
                widgets = item_data["question"]["widgets"]
                for widget_name, widget_data in widgets.items():
                    if widget_data.get("type") == "radio":
                        choices = widget_data.get("options", {}).get("choices", [])
                        for choice in choices:
                            old_content = choice.get("content", "")
                            new_content = clean_content(old_content)
                            if old_content != new_content:
                                choice["content"] = new_content
                                item_modified = True
            
            if item_modified:
                doc["itemData"] = json.dumps(item_data)
                modified = True
                print("Updated itemData field.")
        except Exception as e:
            print(f"Error updating itemData: {e}")

    if modified:
        mongo_db.scraped_questions.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "question.widgets": doc["question"].get("widgets"),
                "perseusItem.question.widgets": doc.get("perseusItem", {}).get("question", {}).get("widgets"),
                "itemData": doc.get("itemData")
            }}
        )
        print("Database updated successfully.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    fix_question_693733e4()
