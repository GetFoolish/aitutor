import json
import os
from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def fix_question_6936552b():
    question_id = "6936552b4d5b9546f400db9d"
    print(f"Fixing question {question_id}...")
    
    # Path to the new image relative to frontend/public
    new_url = "/assets/images/questions/6936552b/function_graph.png"
    
    # Identify the document
    doc = mongo_db.scraped_questions.find_one({"_id": question_id})
    if not doc:
        doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    
    if not doc:
        print("Document not found.")
        return

    def update_widgets(widgets):
        updated = False
        if not widgets:
            return False
            
        for widget_name, widget_data in widgets.items():
            if widget_data.get("type") == "image":
                options = widget_data.get("options", {})
                bg_image = options.get("backgroundImage", {})
                if "url" in bg_image and "ka-perseus-graphie" in bg_image["url"]:
                    print(f"Updating URL for widget {widget_name} from {bg_image['url']} to {new_url}")
                    bg_image["url"] = new_url
                    updated = True
        return updated

    modified = False

    # 1. Update main question widgets
    if "question" in doc and "widgets" in doc["question"]:
        if update_widgets(doc["question"]["widgets"]):
            modified = True

    # 2. Update hints widgets
    if "hints" in doc:
        for i, hint in enumerate(doc["hints"]):
            if "widgets" in hint:
                if update_widgets(hint["widgets"]):
                    modified = True

    # 3. Update perseusItem (if it exists)
    if "perseusItem" in doc:
        p_item = doc["perseusItem"]
        if "question" in p_item and "widgets" in p_item["question"]:
            if update_widgets(p_item["question"]["widgets"]):
                modified = True
        if "hints" in p_item:
            for i, hint in enumerate(p_item["hints"]):
                if "widgets" in hint:
                    if update_widgets(hint["widgets"]):
                        modified = True

    # 4. Update itemData (stringified JSON)
    if "itemData" in doc and doc["itemData"]:
        try:
            item_data = json.loads(doc["itemData"])
            item_modified = False
            
            if "question" in item_data and "widgets" in item_data["question"]:
                if update_widgets(item_data["question"]["widgets"]):
                    item_modified = True
            
            if "hints" in item_data:
                for hint in item_data["hints"]:
                    if "widgets" in hint:
                        if update_widgets(hint["widgets"]):
                            item_modified = True
                            
            if item_modified:
                doc["itemData"] = json.dumps(item_data)
                modified = True
        except Exception as e:
            print(f"Error parsing itemData: {e}")

    if modified:
        mongo_db.scraped_questions.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "question.widgets": doc["question"].get("widgets"),
                "hints": doc.get("hints"),
                "perseusItem": doc.get("perseusItem"),
                "itemData": doc.get("itemData")
            }}
        )
        print("Database updated successfully.")
    else:
        print("No changes were necessary (no web+graphie URLs found or already updated).")

if __name__ == "__main__":
    fix_question_6936552b()
