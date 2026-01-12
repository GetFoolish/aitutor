
import os
import sys
from bson import ObjectId
from dotenv import load_dotenv, find_dotenv

# Add project root to path for shared imports
project_root = os.getcwd()
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(find_dotenv())

from managers.mongodb_manager import mongo_db

def update_question():
    question_id = "693139a04d21167d6d552f1f"
    print(f"Updating question {question_id}...")
    
    doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(question_id)})
    if not doc:
        print("Question not found!")
        return

    # Prepare new choices with images
    # Choice 0: Correct (uploaded_image_0 -> grape_graph_choice_a.png)
    # Choice 1: Distractor (uploaded_image_1 -> grape_graph_choice_b.png)
    # Choice 2: Distractor (uploaded_image_2 -> grape_graph_choice_c.png)
    
    new_choices = [
        {
            "content": "![Grape Graph Choice A](/assets/grape_graph_choice_a.png)",
            "correct": True,
            "clues": []
        },
        {
            "content": "![Grape Graph Choice B](/assets/grape_graph_choice_b.png)",
            "correct": False,
            "clues": []
        },
        {
            "content": "![Grape Graph Choice C](/assets/grape_graph_choice_c.png)",
            "correct": False,
            "clues": []
        }
    ]

    # Update the document
    # Update both the main widgets and the perseusItem for consistency
    mongo_db.scraped_questions.update_one(
        {'_id': ObjectId(question_id)},
        {
            '$set': {
                'question.widgets.radio 1.options.choices': new_choices,
                'perseusItem.question.widgets.radio 1.options.choices': new_choices
            }
        }
    )
    
    print("Successfully updated question choices with reference images.")

if __name__ == "__main__":
    update_question()
