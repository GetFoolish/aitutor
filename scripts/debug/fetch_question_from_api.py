import requests
import json

def fetch_question(question_id):
    url = f"http://localhost:8010/api/question/{question_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        output_file = f"question_{question_id[:8]}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Successfully saved question to {output_file}")
        
        # Print content for quick inspection
        if 'question' in data and 'content' in data['question']:
            print("\n--- Question Content ---")
            print(data['question']['content'])
            print("------------------------\n")
            
    except Exception as e:
        print(f"Error fetching question: {e}")

if __name__ == "__main__":
    fetch_question("69326b802a4ca36772842d03")
