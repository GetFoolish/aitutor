import requests
import json

question_id = "692fb4ae7e334152c5f474dd"
url = f"http://localhost:8010/api/question/{question_id}"

print(f"Fetching from API: {url}...")
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        content = data.get('question', {}).get('content', '')
        print(f"API Content Received: {repr(content)}")
        if '**' in content:
            print("  !! API output still has **")
        else:
            print("  API output IS CLEAN.")
            
        with open('api_response_debug.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Full response saved to api_response_debug.json")
    else:
        print(f"Failed with status: {response.status_code}")
except Exception as e:
    print(f"Error connecting to API: {e}")
