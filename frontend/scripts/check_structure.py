#!/usr/bin/env python3
"""Check the structure of scraped_questions documents."""

import pymongo
import json

MONGO_URI = "mongodb+srv://gagan_db_user:XygEqrowEvCjqJ7l@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority"

def main():
    print("Connecting to MongoDB...")
    client = pymongo.MongoClient(MONGO_URI)
    db = client.ai_tutor

    # Get a sample document
    sample = db.scraped_questions.find_one()

    print("\n=== Document Keys ===")
    print(list(sample.keys()))

    print("\n=== assessmentData type ===")
    assessment = sample.get('assessmentData')
    print(f"Type: {type(assessment)}")

    if isinstance(assessment, str):
        print("assessmentData is a string, parsing...")
        try:
            assessment = json.loads(assessment)
            print(f"Parsed type: {type(assessment)}")
        except Exception as e:
            print(f"Parse error: {e}")

    if isinstance(assessment, dict):
        print(f"\nassessmentData keys: {list(assessment.keys())}")

        # Check item
        item = assessment.get('item')
        if item:
            print(f"\nitem type: {type(item)}")
            if isinstance(item, dict):
                print(f"item keys: {list(item.keys())}")

                # Check question
                question = item.get('question')
                if question:
                    print(f"\nquestion type: {type(question)}")
                    if isinstance(question, dict):
                        print(f"question keys: {list(question.keys())}")

                        widgets = question.get('widgets')
                        if widgets:
                            print(f"\nwidgets type: {type(widgets)}")
                            if isinstance(widgets, dict):
                                print(f"widgets count: {len(widgets)}")
                                for wid, wdata in list(widgets.items())[:3]:
                                    print(f"  {wid}: {wdata.get('type') if isinstance(wdata, dict) else type(wdata)}")

    # Print raw sample (truncated)
    print("\n=== Raw assessmentData (first 2000 chars) ===")
    if isinstance(assessment, dict):
        print(json.dumps(assessment, indent=2)[:2000])
    else:
        print(str(assessment)[:2000])

    client.close()

if __name__ == "__main__":
    main()
