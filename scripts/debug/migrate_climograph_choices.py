from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId
import json

def update_choices(question_id):
    print(f"Updating choices for question: {question_id}")
    
    # New content for choices
    new_choices_content = [
        "![Choice A](/assets/choice_69318c0a_a.png)",
        "![Choice B](/assets/choice_69318c0a_b.png)",
        "![Choice C](/assets/choice_69318c0a_c.png)"
    ]
    
    # Find the question
    question = mongo_db.scraped_questions.find_one({"_id": question_id})
    if not question:
        try:
            question = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass
            
    if not question:
        print("Question not found.")
        return

    # Navigate to the radio widget choices
    widgets = question.get("question", {}).get("widgets", {})
    radio_widget = None
    for widget_key, widget_data in widgets.items():
        if widget_data.get("type") == "radio":
            radio_widget = widget_data
            break
            
    if not radio_widget:
        print("Radio widget not found in question.")
        return
        
    choices = radio_widget.get("options", {}).get("choices", [])
    if len(choices) < 3:
        print(f"Warning: Expected at least 3 choices, found {len(choices)}.")
        
    # Update choice contents
    for i in range(min(len(choices), len(new_choices_content))):
        print(f"Updating choice {i} content...")
        choices[i]["content"] = new_choices_content[i]
        # Keep original correctness (Choice 0 was false in snippet, I should check others)
        
    # Perform the update
    result = mongo_db.scraped_questions.update_one(
        {"_id": question["_id"]},
        {"$set": {
            f"question.widgets.{widget_key}.options.choices": choices
        }}
    )
    
    if result.modified_count > 0:
        print("Successfully updated question choices.")
    else:
        print("Update failed or no changes made.")

if __name__ == "__main__":
    update_choices("69318c0aa58955192117193f")
