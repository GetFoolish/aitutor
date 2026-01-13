from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId
import re

def fix_content_image(question_id):
    print(f"Fixing content image for question: {question_id}")
    
    question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        print("Question not found.")
        return

    content = question.get("question", {}).get("content", "")
    
    # regex to find the graphie image in the content
    # Look for ![alt text](web+graphie://...)
    pattern = r"!\[(.*?)\]\(web\+graphie:\/\/cdn\.kastatic\.org\/ka-perseus-graphie\/a5a556ada1aba9d4ac3351fb326a59882dff77ca\)"
    
    new_url = "/assets/images/replacements/uploaded_image_1768259303195.png"
    
    # Replace with ![alt text](new_url)
    # We use \1 to preserve the alt text captured in group 1
    new_content = re.sub(pattern, f"![\\1]({new_url})", content)
    
    if new_content != content:
        print("Found match. Replacing content...")
        result = mongo_db.scraped_questions.update_one(
            {"_id": question["_id"]},
            {"$set": {"question.content": new_content}}
        )
        print(f"Modified count: {result.modified_count}")
    else:
        print("No matching graphie pattern found in content.")
        print("Current content fragment:")
        print(content[:200]) # Print start of content to verify

if __name__ == "__main__":
    fix_content_image("6930f5599c4e25280b1a447f")
