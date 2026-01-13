from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId
import re

QUESTION_ID = "6930f5599c4e25280b1a447f"
NEW_IMAGE_URL = "/assets/images/replacements/uploaded_image_1768259303195.png"

def fix_question_structure():
    print(f"Refining structure for question: {QUESTION_ID}")
    
    question_doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(QUESTION_ID)})
    if not question_doc:
        print("Question not found.")
        return

    q_data = question_doc.get("question", {})
    content = q_data.get("content", "")
    widgets = q_data.get("widgets", {})
    
    # 1. Extract Alt Text from Markdown Image
    # Pattern to match ![Alt Text](URL)
    # We look for the specific graphie URL we replaced earlier OR the new URL if it was already updated
    # actually, let's just look for *any* image markdown in the intro part
    pattern = r"!\[(.*?)\]\((.*?)\)"
    match = re.search(pattern, content)
    
    start_content = "The function $f$ is defined for all real numbers.\n\n"
    
    alt_text = ""
    if match:
        alt_text = match.group(1)
        print(f"Found alt text: {alt_text[:50]}...")
    else:
        print("Could not extract alt text from content. Using default.")
        alt_text = "Graph of function f"

    # 2. Refine Widget "image 1"
    # We want to make sure it has all necessary fields
    image_widget = {
        "type": "image",
        "alignment": "block",
        "static": False,
        "graded": True,
        "options": {
            "title": "",
            "range": [[-10, 10], [-10, 10]], # Default range
            "box": [325, 325], # Match dimensions from graphie data
            "backgroundImage": {
                "url": NEW_IMAGE_URL,
                "width": 325,
                "height": 325
            },
            "alt": alt_text,
            "labels": [],
            "caption": ""
        },
        "version": {"major": 0, "minor": 0}
    }
    
    widgets["image 1"] = image_widget
    
    # 3. Replace Markdown Image with Widget Placeholder
    # We replace the entire markdown image syntax with [[☃ image 1]]
    if match:
        new_content = content.replace(match.group(0), "[[☃ image 1]]")
    else:
        # Fallback if regex didn't match perfectly, manually reconstruct
        # Assuming the image is between the first two newlines
        parts = content.split("\n\n")
        if len(parts) > 1:
             # Heuristic replacement
             parts[1] = "[[☃ image 1]]"
             new_content = "\n\n".join(parts)
        else:
            print("Could not safely replace content. Aborting content update.")
            new_content = content

    # 4. Update Database
    if new_content != content or widgets.get("image 1") != q_data.get("widgets", {}).get("image 1"):
        print("Updating database...")
        mongo_db.scraped_questions.update_one(
            {"_id": ObjectId(QUESTION_ID)},
            {"$set": {
                "question.content": new_content,
                "question.widgets": widgets
            }}
        )
        print("Update complete.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    fix_question_structure()
