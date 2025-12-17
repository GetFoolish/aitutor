#!/usr/bin/env python3
"""
Analyze questions in MongoDB to find non-math questions and widget type distribution.
"""

import pymongo
from collections import Counter
import json

# MongoDB connection
MONGO_URI = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"

def main():
    print("Connecting to MongoDB...")
    client = pymongo.MongoClient(MONGO_URI)
    db = client.ai_tutor

    # List collections
    print("\n=== Collections in database ===")
    collections = db.list_collection_names()
    for col in collections:
        count = db[col].count_documents({})
        print(f"  {col}: {count} documents")

    # Use scraped_questions collection
    questions_col = db['scraped_questions']
    print(f"\nUsing collection: scraped_questions ({db['scraped_questions'].count_documents({})} documents)")

    # Get sample document structure
    print("\n=== Sample document structure ===")
    sample = questions_col.find_one()
    if sample:
        print(f"Keys: {list(sample.keys())}")
        print(f"_id: {sample.get('_id')}")

    # Analyze widget types
    print("\n=== Widget Type Distribution ===")
    widget_counts = Counter()
    non_math_questions = []

    cursor = questions_col.find({})
    total = 0

    for doc in cursor:
        total += 1
        widgets = None

        # For scraped_questions: assessmentData -> data -> assessmentItem -> item -> itemData (JSON string)
        if 'assessmentData' in doc:
            assessment = doc['assessmentData']
            if isinstance(assessment, dict):
                # Navigate: data -> assessmentItem -> item -> itemData
                data = assessment.get('data', {})
                if isinstance(data, dict):
                    assessment_item = data.get('assessmentItem', {})
                    if isinstance(assessment_item, dict):
                        item = assessment_item.get('item', {})
                        if isinstance(item, dict):
                            item_data_str = item.get('itemData', '')
                            if isinstance(item_data_str, str) and item_data_str:
                                try:
                                    item_data = json.loads(item_data_str)
                                    if isinstance(item_data, dict):
                                        question = item_data.get('question', {})
                                        if isinstance(question, dict):
                                            widgets = question.get('widgets', {})
                                except:
                                    pass

        # Fallback: Try different paths to find widgets
        if not widgets:
            if 'question' in doc and isinstance(doc['question'], dict):
                widgets = doc['question'].get('widgets', {})
            elif 'item_data' in doc:
                item_data = doc['item_data']
                if isinstance(item_data, str):
                    try:
                        item_data = json.loads(item_data)
                    except:
                        pass
                if isinstance(item_data, dict):
                    if 'question' in item_data:
                        widgets = item_data['question'].get('widgets', {})
                    else:
                        widgets = item_data.get('widgets', {})
            elif 'widgets' in doc:
                widgets = doc['widgets']
            elif 'content' in doc and isinstance(doc['content'], dict):
                widgets = doc['content'].get('widgets', {})

        if widgets and isinstance(widgets, dict):
            for widget_id, widget_data in widgets.items():
                if isinstance(widget_data, dict):
                    widget_type = widget_data.get('type', 'unknown')
                    widget_counts[widget_type] += 1

                    # Track non-math widget questions
                    if widget_type in ['sorter', 'orderer', 'matcher', 'categorizer', 'label-image', 'image', 'passage', 'free-response']:
                        non_math_questions.append({
                            '_id': str(doc['_id']),
                            'widget_type': widget_type
                        })

    print(f"Total documents: {total}")
    print("\nWidget type counts:")
    for wtype, count in widget_counts.most_common():
        print(f"  {wtype}: {count}")

    # Print non-math question IDs
    print("\n=== Non-Math Question ObjectIDs ===")
    seen_types = set()
    for q in non_math_questions[:30]:
        if q['widget_type'] not in seen_types or len([x for x in non_math_questions if x['widget_type'] == q['widget_type']]) <= 3:
            print(f"  {q['widget_type']}: {q['_id']}")
            seen_types.add(q['widget_type'])

    # Find specific widget types
    print("\n=== Sample Questions by Widget Type ===")
    for widget_type in ['sorter', 'orderer', 'matcher', 'categorizer', 'interactive-graph', 'plotter', 'label-image']:
        print(f"\n{widget_type}:")
        count = 0
        for q in non_math_questions:
            if q['widget_type'] == widget_type and count < 3:
                print(f"  {q['_id']}")
                count += 1
        if count == 0:
            # Search directly
            for doc in questions_col.find().limit(100):
                widgets = None
                if 'question' in doc and isinstance(doc['question'], dict):
                    widgets = doc['question'].get('widgets', {})
                elif 'item_data' in doc:
                    item_data = doc['item_data']
                    if isinstance(item_data, str):
                        try:
                            item_data = json.loads(item_data)
                        except:
                            continue
                    if isinstance(item_data, dict):
                        if 'question' in item_data:
                            widgets = item_data['question'].get('widgets', {})

                if widgets:
                    for wid, wdata in widgets.items():
                        if isinstance(wdata, dict) and wdata.get('type') == widget_type:
                            print(f"  {doc['_id']}")
                            count += 1
                            break
                if count >= 3:
                    break

    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
