#!/usr/bin/env python3
"""Fetch a specific question by ObjectID."""

import pymongo
import json
from bson import ObjectId

MONGO_URI = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"

def main():
    question_id = "691c6b7341372912898cd346"

    print(f"Fetching question: {question_id}")
    client = pymongo.MongoClient(MONGO_URI)
    db = client.ai_tutor

    # Try to find the question
    question = db.perseus_questions.find_one({"_id": question_id})

    if not question:
        # Try as ObjectId
        try:
            question = db.perseus_questions.find_one({"_id": ObjectId(question_id)})
        except:
            pass

    if question:
        print("\n=== Question Found ===")
        print(f"_id: {question.get('_id')}")
        print(f"slug: {question.get('slug')}")

        # Get widgets
        q = question.get('question', {})
        widgets = q.get('widgets', {})

        print(f"\n=== Widgets ({len(widgets)}) ===")
        for wid, wdata in widgets.items():
            print(f"\nWidget ID: {wid}")
            print(f"  Type: {wdata.get('type')}")
            if wdata.get('type') == 'orderer':
                options = wdata.get('options', {})
                print(f"  Full options JSON:")
                print(json.dumps(options, indent=4))
            elif wdata.get('type') == 'sorter':
                options = wdata.get('options', {})
                print(f"  Options keys: {list(options.keys())}")
                print(f"  correct: {options.get('correct', [])}")
                print(f"  padding: {options.get('padding')}")
                print(f"  layout: {options.get('layout')}")
            else:
                print(f"  Options: {json.dumps(wdata.get('options', {}), indent=4)[:500]}")

        # Print content
        print(f"\n=== Question Content ===")
        content = q.get('content', '')
        print(content[:1000])
    else:
        print("Question not found!")

    client.close()

if __name__ == "__main__":
    main()
