#!/usr/bin/env python3
"""
Replace choice images for question 693751e5150db826a8c256a3
"""
import os
import sys

# Add aitutor root to path (where managers module is located)
# From services/athenaAPI, go up 2 levels to reach aitutor root
aitutor_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, aitutor_root)

from managers.mongodb_manager import mongo_db
from bson import ObjectId

QUESTION_ID = '693751e5150db826a8c256a3'
NEW_CHOICE_1_IMAGE = '/fixed_graphs/bar_chart_choice_1_693751e5.png'
NEW_CHOICE_2_IMAGE = '/fixed_graphs/bar_chart_choice_2_693751e5.png'

print(f"Updating question {QUESTION_ID}...")

# Try string ID first
question = mongo_db.scraped_questions.find_one({'_id': QUESTION_ID})
if not question:
    # Try ObjectId
    try:
        question = mongo_db.scraped_questions.find_one({'_id': ObjectId(QUESTION_ID)})
        is_object_id = True
    except:
        question = None
else:
    is_object_id = False

if not question:
    print(f"ERROR: Question not found in scraped_questions (tried string and ObjectId)")
    exit(1)

# Set the correct query ID for update
query_id = ObjectId(QUESTION_ID) if is_object_id else QUESTION_ID

widgets = question.get('question', {}).get('widgets', {})
radio_widget = widgets.get('radio 1', {})
choices = radio_widget.get('options', {}).get('choices', [])

if len(choices) < 2:
    print(f"ERROR: Expected 2 choices, found {len(choices)}")
    exit(1)

# Update choices
choices[0]['content'] = f"![Bar chart]({NEW_CHOICE_1_IMAGE})"
choices[1]['content'] = f"![Bar chart]({NEW_CHOICE_2_IMAGE})"

# Save to MongoDB
result = mongo_db.scraped_questions.update_one(
    {'_id': query_id},
    {'$set': {'question.widgets.radio 1.options.choices': choices}}
)

if result.modified_count == 1:
    print("✅ SUCCESS: Question updated")
    print(f"   Choice 1: {NEW_CHOICE_1_IMAGE}")
    print(f"   Choice 2: {NEW_CHOICE_2_IMAGE}")
else:
    print("⚠️  No changes made")
