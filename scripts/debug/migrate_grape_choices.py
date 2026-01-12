from managers.mongodb_manager import mongo_db
from bson.objectid import ObjectId

def update_grape_choices(question_id):
    print(f"Updating choices for question: {question_id}")
    
    # New content for choices - simple image references
    new_choices_content = [
        "![Choice A](/assets/grape_graph_choice_a.png)",
        "![Choice B](/assets/grape_graph_choice_b.png)",
        "![Choice C](/assets/grape_graph_choice_c.png)"
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
    radio_widget_key = None
    radio_widget = None
    
    for widget_key, widget_data in widgets.items():
        if widget_data.get("type") == "radio":
            radio_widget_key = widget_key
            radio_widget = widget_data
            break
            
    if not radio_widget:
        print("Radio widget not found in question.")
        return
        
    choices = radio_widget.get("options", {}).get("choices", [])
    if len(choices) < 3:
        print(f"Warning: Expected at least 3 choices, found {len(choices)}.")
        return
        
    # Update choice contents while preserving correctness
    for i in range(min(len(choices), len(new_choices_content))):
        print(f"Updating choice {i} content...")
        choices[i]["content"] = new_choices_content[i]
        
    # Perform the update
    result = mongo_db.scraped_questions.update_one(
        {"_id": question["_id"]},
        {"$set": {
            f"question.widgets.{radio_widget_key}.options.choices": choices
        }}
    )
    
    if result.modified_count > 0:
        print("Successfully updated question choices.")
    else:
        print("Update failed or no changes made.")

if __name__ == "__main__":
    update_grape_choices("6932e9ff488c4a5c22f22f5b")
