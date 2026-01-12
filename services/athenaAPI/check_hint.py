from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['athena']
q = db.questions.find_one({'_id': '69343c30e9b1bbd2029fbc48'})

if q and 'hints' in q:
    print("\n=== HINT 1 (RAW) ===")
    print(repr(q['hints'][0]['content']))
    print("\n=== HINT 1 (FORMATTED) ===")
    print(q['hints'][0]['content'])
else:
    print("Question not found or no hints")
