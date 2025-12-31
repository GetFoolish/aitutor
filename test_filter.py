from managers.mongodb_manager import mongo_db
import json

def test_aggregation(widget_types):
    expanded_types = widget_types
    if 'numeric-input' in widget_types:
        expanded_types.append('input-number')
    
    pipeline = [
        {'$addFields': {
            'widgetsArray': {'$objectToArray': '$question.widgets'}
        }},
        {'$match': {
            'widgetsArray.v.type': {'$in': expanded_types}
        }},
        {'$project': {
            'widgetsArray': 0
        }}
    ]
    
    print(f"Testing aggregation for: {expanded_types}")
    results = list(mongo_db.scraped_questions.aggregate(pipeline))
    print(f"Found {len(results)} results")
    for r in results:
        print(f" - {r.get('questionId')} ({r.get('title')})")

if __name__ == "__main__":
    test_aggregation(['numeric-input'])
