import requests
import json
import re

def find_similar_questions():
    search_url = "http://localhost:8010/api/questions/search"
    payload = {
        "query": "Student name",
        "limit": 50
    }
    
    try:
        print(f"Searching for 'Student name'...")
        response = requests.post(search_url, json=payload)
        response.raise_for_status()
        results = response.json()
        
        found_questions = results.get('results', [])
        print(f"Found {len(found_questions)} questions with 'Student name'.")
        
        affected_ids = []
        for q in found_questions:
            content = q.get('question', {}).get('content', '')
            # Check for **text** pattern
            if re.search(r'\*\*[^*]+\*\*', content):
                q_id = q.get('_id') or q.get('id')
                affected_ids.append(q_id)
                
        print(f"\nIdentified {len(affected_ids)} questions with ** patterns:")
        for qid in affected_ids:
            print(f" - {qid}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_similar_questions()
