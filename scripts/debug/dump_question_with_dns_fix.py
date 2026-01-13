import os
import json
import dns.resolver
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Configure dns.resolver to use Google DNS with TCP and high timeout
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']
dns.resolver.default_resolver.timeout = 10
dns.resolver.default_resolver.lifetime = 60

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, datetime)):
        return obj.isoformat()
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def dump_question(question_id):
    # Load environment variables
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)
    
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
    
    if not mongo_uri:
        print("MONGODB_URI not found in environment")
        return

    print(f"Connecting to MongoDB with custom DNS resolver...")
    try:
        # Pymongo uses dnspython for SRV records. 
        # By setting the default resolver above, it should pick it up.
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db['scraped_questions']
        
        print(f"Fetching question {question_id}...")
        question = collection.find_one({"_id": question_id})
        
        if not question:
            # Try by string ID just in case
            question = collection.find_one({"id": question_id})
        
        if question:
            output_file = f"question_{question_id[:8]}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(question, f, indent=4, default=json_serial, ensure_ascii=False)
            print(f"Successfully dumped question to {output_file}")
            
            # Print content for quick inspection
            if 'itemData' in question:
                item_data = json.loads(question['itemData'])
                if 'question' in item_data and 'content' in item_data['question']:
                    print("\n--- Question Content ---")
                    print(item_data['question']['content'])
                    print("------------------------\n")
        else:
            print(f"Question {question_id} not found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    QUESTION_ID = "69326b802a4ca36772842d03"
    dump_question(QUESTION_ID)
