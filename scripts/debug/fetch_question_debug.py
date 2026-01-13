import requests
import json

def fetch_question(question_id):
    url = f"http://localhost:8010/api/question/{question_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Print content for quick inspection
        if 'question' in data and 'content' in data['question']:
            content = data['question']['content']
            print("\n--- Question Content ---")
            print(content[:1000]) # Print first 1000 chars
            print("------------------------\n")
            
    except Exception as e:
        print(f"Error fetching question: {e}")

if __name__ == "__main__":
    fetch_question("69326b802a4ca36772842d03")
